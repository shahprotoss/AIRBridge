"""Local-network file receiver for AIRBridge.

This is NOT an implementation of Apple's AirDrop or AWDL protocol.
Only a paired browser can offer files, and desktop approval is required.
"""

from __future__ import annotations

import ipaddress
import json
import os
import queue
import re
import secrets
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# These are per-request safety controls, not limits on file count or file size.
MAX_OFFER_METADATA_BYTES = 32 * 1024 * 1024
MAX_UPLOAD_CHUNK_BYTES = 32 * 1024 * 1024
OFFER_TTL = 5 * 60
CHUNK = 512 * 1024
WEB_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "web"
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(cidr) for cidr in
    ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")
)


def safe_filename(raw: str) -> str:
    """Convert untrusted iPhone filenames into safe Windows leaf names."""
    value = str(raw).replace("\\", "/").split("/")[-1]
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip().strip(". ")
    if not value or value in (".", ".."):
        value = "file"
    stem, ext = os.path.splitext(value)
    if stem.upper().split(".")[0] in (
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    ):
        stem = "_" + stem
    return (stem[:140] + ext[:16]).rstrip(". ") or "file"


def local_ipv4() -> str:
    """Prefer the real LAN IP, not Tailscale, WSL, or link-local interfaces."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("1.1.1.1", 80))  # Routes locally; sends no packet.
            address = sock.getsockname()[0]
            if any(ipaddress.ip_address(address) in n for n in PRIVATE_NETWORKS):
                return address
    except OSError:
        pass
    try:
        import psutil

        candidates = []
        for iface, entries in psutil.net_if_addrs().items():
            label = iface.lower()
            if any(part in label for part in ("tailscale", "wsl", "vethernet", "virtual", "loopback")):
                continue
            stats = psutil.net_if_stats().get(iface)
            if stats and not stats.isup:
                continue
            for entry in entries:
                if entry.family != socket.AF_INET:
                    continue
                ip = ipaddress.ip_address(entry.address)
                if any(ip in net for net in PRIVATE_NETWORKS[:-1]):
                    candidates.append(str(ip))
        if candidates:
            return candidates[0]
    except (OSError, ImportError, ValueError):
        pass
    return "127.0.0.1"


@dataclass
class Offer:
    id: str
    peer: str
    label: str
    files: list[dict]
    created: float = field(default_factory=time.monotonic)
    state: str = "pending"
    completed: set[int] = field(default_factory=set)
    in_progress: set[int] = field(default_factory=set)
    offsets: dict[int, int] = field(default_factory=dict)
    part_paths: dict[int, Path] = field(default_factory=dict)
    bytes_received: int = 0
    error: str = ""

    @property
    def total(self) -> int:
        return sum(item["size"] for item in self.files)


class DropServer:
    def __init__(self, save_dir: Path, bind: str = "0.0.0.0", port: int = 0):
        self.save_dir = Path(save_dir)
        self.bind = bind
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.offers: dict[str, Offer] = {}
        self.events: queue.Queue[tuple] = queue.Queue()
        self.history: list[dict] = []
        self.lock = threading.RLock()
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self):
        self.save_dir.mkdir(parents=True, exist_ok=True)
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "AIRBridge/1.3"
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                # Never log private pairing tokens appearing in request URLs.
                pass

            def _local_client(self):
                try:
                    peer = ipaddress.ip_address(self.client_address[0])
                    return any(peer in network for network in PRIVATE_NETWORKS)
                except ValueError:
                    return False

            def _authorized(self):
                token = self.headers.get("X-Drop-Token", "")
                return self._local_client() and secrets.compare_digest(token, receiver.token)

            def _send(self, code: int, content: bytes, mimetype: str = "application/json"):
                self.send_response(code)
                self.send_header("Content-Type", mimetype)
                self.send_header("Content-Length", str(len(content)))
                # Reuse the connection for subsequent chunks instead of one
                # TCP connection per chunk (which is costly over Wi-Fi).
                self.send_header("Connection", "close" if self.close_connection else "keep-alive")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                    "form-action 'none'; frame-ancestors 'none'"
                )
                self.end_headers()
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _json(self, code: int, payload: dict):
                self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

            def _fail(self, code: int, message: str):
                # Rejecting a POST before its body has been read must close
                # the socket or leftover bytes could be misparsed as HTTP.
                if self.command == "POST":
                    self.close_connection = True
                self._json(code, {"error": message})

            def _route(self):
                return urlsplit(self.path)

            def do_GET(self):
                route = self._route()
                if not self._local_client():
                    return self._fail(403, "Only local-network devices are allowed")
                if route.path == "/":
                    access = parse_qs(route.query).get("k", [""])[0]
                    if not secrets.compare_digest(access, receiver.token):
                        return self._fail(403, "Scan the QR code displayed on your PC")
                    return self._send(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
                if route.path in ("/style.css", "/client.js"):
                    name = route.path[1:]
                    mime = "text/css; charset=utf-8" if name.endswith(".css") else "text/javascript; charset=utf-8"
                    return self._send(200, (WEB_DIR / name).read_bytes(), mime)
                if route.path == "/api/status":
                    if not self._authorized():
                        return self._fail(403, "Invalid pairing session")
                    offer_id = parse_qs(route.query).get("id", [""])[0]
                    with receiver.lock:
                        offer = receiver.offers.get(offer_id)
                        if not offer or offer.peer != self.client_address[0]:
                            return self._fail(404, "Transfer not found")
                        receiver._expire(offer)
                        result = {
                            "state": offer.state, "progress": offer.bytes_received,
                            "total": offer.total, "completed": len(offer.completed),
                            "error": offer.error,
                        }
                        file_index = parse_qs(route.query).get("index", [None])[0]
                        if file_index is not None:
                            try:
                                idx = int(file_index)
                            except ValueError:
                                return self._fail(400, "Invalid file index")
                            if idx < 0 or idx >= len(offer.files):
                                return self._fail(400, "Invalid file index")
                            result["file_offset"] = offer.offsets.get(idx, 0)
                            result["file_done"] = idx in offer.completed
                        return self._json(200, result)
                return self._fail(404, "Not found")

            def do_POST(self):
                route = self._route()
                if not self._authorized():
                    return self._fail(403, "Invalid pairing session")
                if route.path == "/api/offer":
                    return self._create_offer()
                if route.path == "/api/upload":
                    return self._upload(parse_qs(route.query))
                return self._fail(404, "Not found")

            def _create_offer(self):
                try:
                    length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    length = -1
                if not (0 < length <= MAX_OFFER_METADATA_BYTES):
                    return self._fail(413, "File list metadata is too large")
                try:
                    body = json.loads(self.rfile.read(length))
                    files = body["files"]
                    if not isinstance(files, list) or not files:
                        raise ValueError("Choose at least one file")
                    normalized = []
                    for item in files:
                        size = item["size"]
                        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                            raise ValueError("Invalid file size")
                        name = safe_filename(item["name"])
                        normalized.append({"name": name, "size": size})
                except (ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
                    return self._fail(400, f"Invalid file selection: {exc}")
                user_agent = self.headers.get("User-Agent", "").lower()
                label = "iPhone" if "iphone" in user_agent else ("iPad" if "ipad" in user_agent else "Peranti")
                offer = Offer(
                    id=uuid.uuid4().hex,
                    peer=self.client_address[0],
                    label=label,
                    files=normalized,
                )
                with receiver.lock:
                    receiver.offers[offer.id] = offer
                    receiver.events.put(("offer", offer.id))
                return self._json(201, {"id": offer.id, "state": offer.state})

            def _upload(self, query: dict[str, list[str]]):
                offer_id = query.get("id", [""])[0]
                try:
                    idx = int(query.get("index", ["-1"])[0])
                    offset = int(query.get("offset", ["0"])[0])
                    content_length = int(self.headers.get("Content-Length", "-1"))
                except ValueError:
                    return self._fail(400, "Invalid upload size or offset")
                if not 0 <= content_length <= MAX_UPLOAD_CHUNK_BYTES or offset < 0:
                    return self._fail(413, "Chunk too large or invalid")
                with receiver.lock:
                    offer = receiver.offers.get(offer_id)
                    if not offer or offer.peer != self.client_address[0]:
                        return self._fail(404, "Transfer not found")
                    receiver._expire(offer)
                    if offer.state != "accepted":
                        return self._fail(409, "Transfer was not approved")
                    if idx < 0 or idx >= len(offer.files) or idx in offer.completed or idx in offer.in_progress:
                        return self._fail(409, "Invalid or repeated file")
                    item = offer.files[idx]
                    expected = offer.offsets.get(idx, 0)
                    if offset != expected:
                        return self._fail(409, "Unexpected chunk offset")
                    if offset + content_length > item["size"]:
                        return self._fail(400, "Chunk exceeds approved file size")
                    if content_length == 0 and offset != item["size"]:
                        return self._fail(400, "Unexpected empty chunk")
                    offer.in_progress.add(idx)

                try:
                    with receiver.lock:
                        directory = receiver.save_dir
                        directory.mkdir(parents=True, exist_ok=True)
                        part = offer.part_paths.get(idx)
                        if part is None:
                            part = directory / (".dropbridge-" + uuid.uuid4().hex + ".part")
                            offer.part_paths[idx] = part
                    self.connection.settimeout(180)
                    with part.open("wb" if offset == 0 else "r+b") as output:
                        if offset:
                            output.seek(0, os.SEEK_END)
                            if output.tell() != offset:
                                raise OSError("Incomplete file does not match expected offset")
                        remaining = content_length
                        while remaining:
                            chunk = self.rfile.read(min(CHUNK, remaining))
                            if not chunk:
                                raise ConnectionError("Upload interrupted")
                            output.write(chunk)
                            remaining -= len(chunk)
                    with receiver.lock:
                        if offset + content_length == item["size"]:
                            destination = receiver._unique_destination(directory, item["name"])
                            os.replace(part, destination)
                            offer.part_paths.pop(idx, None)
                            offer.offsets[idx] = offset + content_length
                            offer.bytes_received += content_length
                            offer.completed.add(idx)
                            if len(offer.completed) == len(offer.files):
                                offer.state = "done"
                            receiver.history.insert(0, {
                                "name": destination.name, "path": str(destination),
                                "size": item["size"], "when": time.time(),
                            })
                            receiver.history[:] = receiver.history[:100]
                            receiver.events.put(("received", offer_id, str(destination)))
                            return self._json(200, {
                                "ok": True, "done": True, "saved_as": destination.name
                            })
                        offer.offsets[idx] = offset + content_length
                        offer.bytes_received += content_length
                        return self._json(200, {
                            "ok": True, "done": False, "next_offset": offer.offsets[idx]
                        })
                except (OSError, ConnectionError, TimeoutError) as exc:
                    # Restore the previous offset so the client can retry this chunk.
                    try:
                        part = offer.part_paths.get(idx)
                        if part is not None and part.exists():
                            with part.open("r+b") as output:
                                output.truncate(offset)
                    except OSError:
                        pass
                    with receiver.lock:
                        offer.error = str(exc)
                    return self._fail(500, "Could not save this chunk. Please retry")
                finally:
                    with receiver.lock:
                        offer.in_progress.discard(idx)

        class Server(ThreadingHTTPServer):
            daemon_threads = True

        self.httpd = Server((self.bind, self.port), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def _expire(self, offer: Offer):
        if offer.state == "pending" and time.monotonic() - offer.created > OFFER_TTL:
            offer.state = "expired"

    def _unique_destination(self, directory: Path, name: str) -> Path:
        destination = directory / safe_filename(name)
        stem, ext = destination.stem, destination.suffix
        counter = 1
        while destination.exists():
            destination = directory / f"{stem} ({counter}){ext}"
            counter += 1
        return destination

    def pending(self) -> list[Offer]:
        with self.lock:
            for offer in self.offers.values():
                self._expire(offer)
            return sorted(
                (offer for offer in self.offers.values() if offer.state == "pending"),
                key=lambda offer: offer.created,
            )

    def active(self) -> list[Offer]:
        with self.lock:
            return [o for o in self.offers.values() if o.state == "accepted"]

    def approve(self, offer_id: str, allow: bool) -> bool:
        with self.lock:
            offer = self.offers.get(offer_id)
            if not offer:
                return False
            self._expire(offer)
            if offer.state != "pending":
                return False
            offer.state = "accepted" if allow else "declined"
            self.events.put(("decision", offer.id, offer.state))
            return True

    def url(self) -> str:
        return f"http://{local_ipv4()}:{self.port}/?k={self.token}"

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)
        # Clean up incomplete transfers from this application session.
        with self.lock:
            leftovers = [
                path for offer in self.offers.values()
                for path in offer.part_paths.values()
            ]
        for path in leftovers:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

"""AIRBridge — a premium local transfer receiver for Windows 11.

AIRBridge accepts browser uploads over the user's trusted local network.
It is not an implementation of the Apple AirDrop protocol.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import qrcode
from PIL import Image

from transfer_server import DropServer, local_ipv4
from localization import LANGUAGES, translate


RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ICON_PATH = RESOURCE_DIR / "assets" / "airbridge.ico"
LOGO_PATH = RESOURCE_DIR / "assets" / "airbridge.png"
APP_DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AIRBridge"
CONFIG = APP_DATA / "settings.json"
LEGACY_CONFIG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "DropBridge" / "settings.json"
PREVIOUS_SAVE = Path.home() / "Downloads" / "DropBridge"
DEFAULT_SAVE = PREVIOUS_SAVE if PREVIOUS_SAVE.exists() else Path.home() / "Downloads" / "AIRBridge"

BG = "#F5F5F7"
SURFACE = "#FFFFFF"
INK = "#1D1D1F"
MUTED = "#7A7D85"
SUBTLE = "#A2A7B0"
LINE = "#E7E9EF"
BLUE = "#007AFF"
BLUE_HOVER = "#006AE1"
PALE_BLUE = "#EFF6FF"
GREEN = "#30B768"
PALE_GREEN = "#EAF9F0"
CARD_BG = "#F8F9FC"
FONT = "Segoe UI"


def format_bytes(value: int) -> str:
    number = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB", "EB"):
        if number < 1024 or unit == "EB":
            return f"{number:.1f} {unit}"
        number /= 1024
    return f"{number:.1f} EB"


def load_config() -> dict:
    for path in (CONFIG, LEGACY_CONFIG):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
        except (OSError, ValueError):
            pass
    return {}


def save_config(settings: dict):
    APP_DATA.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def open_folder(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    os.startfile(str(folder))


def txt(parent, text, size=12, color=INK, weight="normal", **kwargs):
    return ctk.CTkLabel(
        parent, text=text, font=ctk.CTkFont(family=FONT, size=size, weight=weight),
        text_color=color, **kwargs,
    )


def pill(parent, label, callback, primary=False, **kwargs):
    button_height = kwargs.pop("height", 40)
    button_radius = kwargs.pop("corner_radius", 16)
    return ctk.CTkButton(
        parent, text=label, command=callback,
        fg_color=BLUE if primary else "#F0F2F7",
        hover_color=BLUE_HOVER if primary else "#E5EAF3",
        text_color=SURFACE if primary else INK,
        corner_radius=button_radius, height=button_height,
        font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
        **kwargs,
    )


class AIRBridgeApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        super().__init__()
        settings = load_config()
        self.language = settings.get("language", "en")
        if self.language not in LANGUAGES:
            self.language = "en"
        self.title(self.t("window_title"))
        self.geometry("1100x750")
        self.minsize(920, 660)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.iconbitmap(str(ICON_PATH))
        except (OSError, tk.TclError):
            pass

        self.save_dir = Path(settings.get("save_dir") or DEFAULT_SAVE)
        self.receiver = DropServer(self.save_dir).start()
        self.pending_signature: tuple[str, ...] = ()
        self.history_signature: tuple[tuple[str, float], ...] = ()
        self.notified: set[str] = set()
        self.status_var = tk.StringVar(value=self.t("status_ready"))
        self.folder_var = tk.StringVar(value=str(self.save_dir))
        self.ip_var = tk.StringVar(value="Connecting…")
        self.address_var = tk.StringVar()
        self.qr_image = None
        self.logo_image = None
        self.toast_window = None
        self._status_reset_id = None

        self._build()
        self._refresh_qr()
        self._poll_after_id = self.after(250, self._poll)

    def t(self, key: str, **values) -> str:
        return translate(self.language, key, **values)

    def _set_language(self, display_name: str):
        selected = "ms" if display_name == "Bahasa Melayu" else "en"
        if selected == self.language:
            return
        self.language = selected
        save_config({"save_dir": str(self.save_dir), "language": self.language})
        self.title(self.t("window_title"))
        self.status_var.set(self.t("status_ready"))
        for widget in list(self.winfo_children()):
            widget.destroy()
        self.pending_signature = ()
        self.history_signature = ()
        self._build()
        self._refresh_qr()
        self._display_pending()
        self._display_history()
        self._display_progress()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Premium, restrained title row.
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(22, 14))
        header.grid_columnconfigure(1, weight=1)
        if LOGO_PATH.exists():
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(LOGO_PATH), size=(43, 43),
            )
            ctk.CTkLabel(header, image=self.logo_image, text="").grid(
                row=0, column=0, rowspan=2, sticky="w", padx=(0, 12)
            )
        else:
            txt(header, "↗", 30, BLUE, "bold").grid(
                row=0, column=0, rowspan=2, sticky="w", padx=(0, 12)
            )
        txt(header, "AIRBridge", 23, INK, "bold").grid(
            row=0, column=1, sticky="sw"
        )
        txt(header, self.t("tagline"), 10, MUTED).grid(
            row=1, column=1, sticky="nw", pady=(1, 0)
        )
        self.language_picker = ctk.CTkSegmentedButton(
            header, values=["English", "Bahasa Melayu"],
            command=self._set_language, width=195, height=36,
            corner_radius=14, fg_color="#EDF1F7",
            selected_color=BLUE, selected_hover_color=BLUE_HOVER,
            unselected_color="#EDF1F7", unselected_hover_color="#E0E7F1",
            text_color=INK, text_color_disabled=MUTED,
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
        )
        self.language_picker.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 12))
        self.language_picker.set("Bahasa Melayu" if self.language == "ms" else "English")
        online = ctk.CTkFrame(header, fg_color=PALE_GREEN, corner_radius=22)
        online.grid(row=0, column=3, rowspan=2, sticky="e", padx=(0, 12))
        txt(online, self.t("available"), 11, GREEN, "bold").pack(padx=14, pady=10)
        pill(header, self.t("open_received"), lambda: open_folder(self.save_dir),
             width=175).grid(row=0, column=4, rowspan=2, sticky="e")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=34, pady=(2, 16))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=340)
        body.grid_columnconfigure(1, weight=1)

        # Left card: pair by QR, with generous whitespace and subtle hierarchy.
        left = ctk.CTkFrame(
            body, fg_color=SURFACE, corner_radius=26,
            border_width=1, border_color=LINE, width=340,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left.grid_propagate(False)
        txt(left, self.t("connect_heading"), 10, BLUE, "bold").pack(
            anchor="w", padx=28, pady=(30, 10)
        )
        txt(left, self.t("connect_title"), 25, INK, "bold",
            justify="left").pack(anchor="w", padx=28)
        txt(left, self.t("connect_hint"),
            12, MUTED, justify="left").pack(anchor="w", padx=28, pady=(9, 13))

        qr_wrap = ctk.CTkFrame(
            left, fg_color=BG, border_color=LINE, border_width=1,
            corner_radius=20, width=262, height=262,
        )
        qr_wrap.pack(padx=22, pady=(2, 16))
        qr_wrap.pack_propagate(False)
        self.qr_label = ctk.CTkLabel(qr_wrap, text="", fg_color="transparent")
        self.qr_label.pack(expand=True)

        network = ctk.CTkFrame(left, fg_color=CARD_BG, corner_radius=14)
        network.pack(fill="x", padx=25, pady=(3, 12))
        txt(network, "●", 13, GREEN).pack(side="left", padx=(14, 6), pady=11)
        txt(network, self.t("private_network"), 11, INK, "bold").pack(
            side="left", pady=11
        )
        txt(network, "", 11, MUTED, textvariable=self.ip_var).pack(
            side="right", padx=(5, 14), pady=11
        )
        self.copy_button = pill(
            left, self.t("copy_link"), self._copy_url, primary=True, height=44
        )
        self.copy_button.pack(fill="x", padx=25, pady=(0, 7))
        txt(left, self.t("privacy"),
            10, MUTED, wraplength=285).pack(anchor="w", padx=27, pady=(7, 18))

        # Right side is scrollable so the interface remains useful on small screens.
        right = ctk.CTkScrollableFrame(
            body, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#DDE2EA",
            scrollbar_button_hover_color="#C4CDD8",
        )
        right.grid(row=0, column=1, sticky="nsew")

        # Main status panel.
        status_card = ctk.CTkFrame(
            right, fg_color=PALE_BLUE, corner_radius=24,
            border_width=1, border_color="#E0EEFF",
        )
        status_card.pack(fill="x", padx=(0, 2), pady=(0, 13))
        state_top = ctk.CTkFrame(status_card, fg_color="transparent")
        state_top.pack(fill="x", padx=24, pady=(20, 4))
        self.hero_icon = ctk.CTkLabel(
            state_top, text="✓", width=48, height=48,
            corner_radius=15, fg_color=BLUE, text_color=SURFACE,
            font=ctk.CTkFont(family=FONT, size=23, weight="bold"),
        )
        self.hero_icon.pack(side="left", padx=(0, 14))
        title_wrap = ctk.CTkFrame(state_top, fg_color="transparent")
        title_wrap.pack(side="left", fill="x", expand=True)
        self.hero_title = txt(title_wrap, self.t("ready_title"), 20, INK, "bold")
        self.hero_title.pack(anchor="w")
        self.hero_caption = txt(title_wrap, self.t("ready_caption"),
                                11, MUTED)
        self.hero_caption.pack(anchor="w", pady=(3, 0))
        self.main_progress = ctk.CTkProgressBar(
            status_card, height=7, fg_color="#D7E7F9",
            progress_color=BLUE, corner_radius=8,
        )
        self.main_progress.set(0)
        self.main_progress.pack(fill="x", padx=25, pady=(15, 7))
        self.hero_progress = txt(status_card, self.t("ready_progress"),
                                 11, MUTED)
        self.hero_progress.pack(anchor="w", padx=25, pady=(0, 19))

        # Destination card.
        dest = ctk.CTkFrame(
            right, fg_color=SURFACE, corner_radius=22,
            border_width=1, border_color=LINE,
        )
        dest.pack(fill="x", padx=(0, 2), pady=(0, 13))
        dest_header = ctk.CTkFrame(dest, fg_color="transparent")
        dest_header.pack(fill="x", padx=21, pady=(15, 4))
        txt(dest_header, self.t("save_location"), 10, MUTED, "bold").pack(side="left")
        pill(dest_header, self.t("change"), self._choose_folder,
             width=76, height=30, corner_radius=12).pack(side="right")
        txt(dest, "▣  " + str(self.save_dir), 11, INK,
            textvariable=self.folder_var, wraplength=515, justify="left").pack(
            anchor="w", padx=23, pady=(3, 18)
        )

        # Approval queue.
        pending = ctk.CTkFrame(
            right, fg_color=SURFACE, corner_radius=22,
            border_width=1, border_color=LINE,
        )
        pending.pack(fill="x", padx=(0, 2), pady=(0, 13))
        pending_header = ctk.CTkFrame(pending, fg_color="transparent")
        pending_header.pack(fill="x", padx=22, pady=(17, 8))
        txt(pending_header, self.t("incoming"), 16, INK, "bold").pack(side="left")
        self.request_count = txt(pending_header, self.t("pending_count", count=0), 10, MUTED)
        self.request_count.pack(side="right", pady=3)
        self.pending_box = ctk.CTkFrame(
            pending, fg_color=CARD_BG, corner_radius=14,
        )
        self.pending_box.pack(fill="x", padx=19, pady=(0, 19))
        txt(self.pending_box, self.t("empty_pending"),
            11, MUTED, wraplength=425).pack(
            anchor="w", padx=16, pady=18
        )

        # Recent activity.
        history = ctk.CTkFrame(
            right, fg_color=SURFACE, corner_radius=22,
            border_width=1, border_color=LINE,
        )
        history.pack(fill="both", expand=True, padx=(0, 2), pady=(0, 3))
        history_header = ctk.CTkFrame(history, fg_color="transparent")
        history_header.pack(fill="x", padx=22, pady=(18, 9))
        txt(history_header, self.t("recent"), 16, INK, "bold").pack(side="left")
        self.activity_count = txt(history_header, self.t("recent_initial"), 10, MUTED)
        self.activity_count.pack(side="right", pady=3)
        self.history_box = ctk.CTkFrame(
            history, fg_color="transparent", corner_radius=0,
        )
        self.history_box.pack(fill="x", padx=20, pady=(0, 14))
        txt(self.history_box, self.t("empty_history"), 11, MUTED).pack(
            anchor="w", pady=10
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=36, pady=(0, 17))
        txt(footer, "●", 11, GREEN).pack(side="left")
        txt(footer, "", 11, MUTED, textvariable=self.status_var).pack(
            side="left", padx=(7, 0)
        )
        txt(footer, self.t("footer"),
            10, SUBTLE).pack(side="right")

    def _refresh_qr(self):
        uri = self.receiver.url(self.language)
        ip = local_ipv4()
        self.ip_var.set(ip if ip != "127.0.0.1" else self.t("no_lan"))
        self.address_var.set(uri)
        qr = qrcode.QRCode(
            box_size=8, border=2,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        image = qr.make_image(fill_color=INK, back_color="white").convert("RGB")
        image.thumbnail((232, 232))
        # Keep a reference to CTkImage, otherwise Tk image objects disappear.
        self.qr_image = ctk.CTkImage(
            light_image=image, dark_image=image, size=(232, 232)
        )
        self.qr_label.configure(image=self.qr_image)

    def _copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.receiver.url(self.language))
        self.status_var.set(self.t("status_copied"))
        self.copy_button.configure(text=self.t("copied"))
        self.after(2000, self._restore_copy_button)

    def _restore_copy_button(self):
        if self.copy_button.winfo_exists():
            self.copy_button.configure(text=self.t("copy_link"))

    def _choose_folder(self):
        directory = filedialog.askdirectory(initialdir=str(self.save_dir))
        if directory:
            self.save_dir = Path(directory)
            self.receiver.save_dir = self.save_dir
            self.folder_var.set(str(self.save_dir))
            save_config({"save_dir": str(self.save_dir), "language": self.language})
            self.status_var.set(self.t("status_folder"))

    def _poll(self):
        try:
            while True:
                event = self.receiver.events.get_nowait()
                kind = event[0]
                if kind == "offer":
                    self.bell()
                    self.lift()
                if kind == "received":
                    offer_id = event[1]
                    with self.receiver.lock:
                        offer = self.receiver.offers.get(offer_id)
                        complete = offer and offer.state == "done"
                    if complete and offer_id not in self.notified:
                        self.notified.add(offer_id)
                        self._on_complete(offer)
        except queue.Empty:
            pass
        self._display_pending()
        self._display_history()
        self._display_progress()
        self._poll_after_id = self.after(450, self._poll)

    def _display_pending(self):
        pending = self.receiver.pending()
        signature = tuple(item.id for item in pending)
        if signature == self.pending_signature:
            return
        self.pending_signature = signature
        self.request_count.configure(
            text=self.t("pending_count", count=len(pending))
        )
        for child in self.pending_box.winfo_children():
            child.destroy()
        if not pending:
            txt(self.pending_box, self.t("empty_pending"),
                11, MUTED, wraplength=420).pack(
                anchor="w", padx=16, pady=18
            )
            return
        offer = pending[0]
        txt(self.pending_box,
            self.t("offer_title", device=offer.label, count=len(offer.files)),
            13, INK, "bold").pack(anchor="w", padx=16, pady=(16, 5))
        preview = ", ".join(item["name"] for item in offer.files[:3])
        if len(offer.files) > 3:
            preview += " …"
        txt(self.pending_box, preview + "  •  " + format_bytes(offer.total),
            11, MUTED, wraplength=420, justify="left").pack(
            anchor="w", padx=16, pady=(0, 12)
        )
        actions = ctk.CTkFrame(self.pending_box, fg_color="transparent")
        actions.pack(anchor="w", padx=16, pady=(0, 15))
        pill(actions, self.t("accept"), lambda oid=offer.id: self._decide(oid, True),
             primary=True, width=108, height=35).pack(side="left", padx=(0, 9))
        pill(actions, self.t("decline"), lambda oid=offer.id: self._decide(oid, False),
             width=99, height=35).pack(side="left")
        if len(pending) > 1:
            txt(self.pending_box, self.t("more_requests", count=len(pending) - 1),
                10, MUTED).pack(anchor="w", padx=16, pady=(0, 12))
        self.status_var.set(self.t("status_request", device=offer.label))

    def _decide(self, offer_id: str, accepted: bool):
        if self.receiver.approve(offer_id, accepted):
            self.status_var.set(
                self.t("status_accepted" if accepted else "status_declined")
            )
            self._display_pending()

    def _display_history(self):
        with self.receiver.lock:
            records = list(self.receiver.history[:7])
        signature = tuple((item["path"], item["when"]) for item in records)
        if signature == self.history_signature:
            return
        self.history_signature = signature
        self.activity_count.configure(
            text=self.t("recent_count", count=len(records))
        )
        for child in self.history_box.winfo_children():
            child.destroy()
        if not records:
            txt(self.history_box, self.t("empty_history"),
                11, MUTED).pack(anchor="w", pady=10)
            return
        for entry in records:
            row = ctk.CTkFrame(
                self.history_box, fg_color=CARD_BG, corner_radius=12,
            )
            row.pack(fill="x", pady=3)
            icon = ctk.CTkLabel(
                row, text="↓", text_color=BLUE, fg_color="#E8F1FF",
                corner_radius=11, width=38, height=38,
                font=ctk.CTkFont(family=FONT, size=19, weight="bold"),
            )
            icon.pack(side="left", padx=(11, 12), pady=9)
            middle = ctk.CTkFrame(row, fg_color="transparent")
            middle.pack(side="left", fill="x", expand=True, pady=8)
            name = entry["name"]
            if len(name) > 45:
                name = name[:30] + "…" + name[-12:]
            txt(middle, name, 12, INK, "bold").pack(anchor="w")
            txt(middle, format_bytes(entry["size"]), 10, MUTED).pack(
                anchor="w", pady=(2, 0)
            )
            stamp = datetime.fromtimestamp(entry["when"]).strftime("%H:%M")
            txt(row, stamp, 10, MUTED).pack(side="right", padx=14)

    def _display_progress(self):
        active = self.receiver.active()
        if not active:
            return
        total = sum(item.total for item in active)
        done = sum(item.bytes_received for item in active)
        progress = done / total if total > 0 else 0.0
        self.main_progress.set(min(1.0, max(0.0, progress)))
        self.hero_title.configure(text=self.t("receiving_title"))
        self.hero_caption.configure(
            text=self.t("receiving_caption", count=len(active))
        )
        self.hero_progress.configure(
            text=self.t(
                "receiving_progress", done=format_bytes(done),
                total=format_bytes(total),
            )
        )

    def _on_complete(self, offer):
        count = len(offer.files)
        detail = self.t(
            "complete_detail", count=count, size=format_bytes(offer.total)
        )
        self.main_progress.set(1)
        self.hero_icon.configure(text="✓", fg_color=GREEN)
        self.hero_title.configure(text=self.t("complete_title"))
        self.hero_caption.configure(text=self.t("complete_caption"))
        self.hero_progress.configure(text=detail)
        self.status_var.set(self.t("success_status", count=count))
        self._show_toast(self.t("complete_title"), detail)
        threading.Thread(
            target=self._native_toast, args=(count, offer.total),
            daemon=True,
        ).start()
        if self._status_reset_id is not None:
            self.after_cancel(self._status_reset_id)
        self._status_reset_id = self.after(6500, self._reset_status)

    def _reset_status(self):
        self._status_reset_id = None
        if self.receiver.active():
            return
        self.main_progress.set(0)
        self.hero_icon.configure(text="✓", fg_color=BLUE)
        self.hero_title.configure(text=self.t("ready_title"))
        self.hero_caption.configure(text=self.t("ready_caption"))
        self.hero_progress.configure(text=self.t("ready_progress"))
        self.status_var.set(self.t("status_ready"))

    def _show_toast(self, title: str, detail: str):
        """Reliable local popup even when system notifications are disabled."""
        try:
            if self.toast_window and self.toast_window.winfo_exists():
                self.toast_window.destroy()
        except tk.TclError:
            pass
        toast = tk.Toplevel(self)
        self.toast_window = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=LINE)
        width, height = 360, 110
        screen_w, screen_h = toast.winfo_screenwidth(), toast.winfo_screenheight()
        toast.geometry(
            f"{width}x{height}+{screen_w - width - 26}+{screen_h - height - 62}"
        )
        frame = ctk.CTkFrame(
            toast, fg_color=SURFACE, corner_radius=18,
            border_width=1, border_color=LINE,
        )
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        ctk.CTkLabel(
            frame, text="✓", width=47, height=47, fg_color=PALE_GREEN,
            corner_radius=20, text_color=GREEN,
            font=ctk.CTkFont(family=FONT, size=24, weight="bold"),
        ).pack(side="left", padx=(17, 13), pady=20)
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(side="left", fill="x", expand=True)
        txt(content, title, 15, INK, "bold").pack(anchor="w")
        txt(content, detail, 11, MUTED, wraplength=225,
            justify="left").pack(anchor="w", pady=(4, 0))
        toast.after(5500, lambda: toast.destroy() if toast.winfo_exists() else None)

    def _native_toast(self, count: int, total: int):
        """Show the native Windows notification when permitted by the OS."""
        try:
            from winotify import Notification
            native = Notification(
                app_id="AIRBridge",
                title=self.t("native_title"),
                msg=self.t(
                    "native_message", count=count, size=format_bytes(total)
                ),
                icon=str(LOGO_PATH) if LOGO_PATH.exists() else "",
                duration="short",
            )
            native.show()
        except Exception:
            # Windows Focus Assist, disabled notifications, or an unpackaged
            # application can prevent native toast delivery. Local toast remains.
            pass

    def close(self):
        if getattr(self, "_poll_after_id", None) is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._status_reset_id is not None:
            self.after_cancel(self._status_reset_id)
            self._status_reset_id = None
        if self.toast_window is not None:
            try:
                if self.toast_window.winfo_exists():
                    self.toast_window.destroy()
            except tk.TclError:
                pass
        self.receiver.stop()
        self.destroy()


def main():
    try:
        AIRBridgeApp().mainloop()
    except OSError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("AIRBridge", translate("en", "launch_error", error=exc))


if __name__ == "__main__":
    main()

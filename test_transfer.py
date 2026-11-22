"""Integration tests for approval, authentication, and disk writes."""
import http.client
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from transfer_server import DropServer, safe_filename


class DropServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = DropServer(Path(self.temp.name), bind="127.0.0.1").start()

    def tearDown(self):
        self.server.stop()
        self.temp.cleanup()

    def request(self, method, url, data=None, token=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=4)
        headers = {"X-Drop-Token": self.server.token if token else "invalid"}
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        conn.request(method, url, body=data, headers=headers)
        response = conn.getresponse()
        content = response.read()
        code = response.status
        conn.close()
        return code, json.loads(content) if response.getheader("Content-Type", "").startswith("application/json") else content

    def test_requires_pairing(self):
        code, _ = self.request("POST", "/api/offer", {"files": [{"name": "hello.txt", "size": 5}]}, token=False)
        self.assertEqual(code, 403)
        code, _ = self.request("GET", "/")
        self.assertEqual(code, 403)
        code, _ = self.request("GET", "/?k=" + self.server.token)
        self.assertEqual(code, 200)
        code, sender_script = self.request("GET", "/i18n.js")
        self.assertEqual(code, 200)
        self.assertIn(b"Connected locally", sender_script)

    def test_qr_language_hint(self):
        self.assertIn("&lang=ms", self.server.url("ms"))
        self.assertIn("&lang=en", self.server.url("en"))
        self.assertNotIn("&lang=", self.server.url("invalid"))

    def test_approval_and_file_upload(self):
        code, offer = self.request("POST", "/api/offer", {"files": [{"name": "../../photo.txt", "size": 5}]})
        self.assertEqual(code, 201)
        offer_id = offer["id"]
        url = "/api/upload?id=" + offer_id + "&index=0"
        code, _ = self.request("POST", url, b"hello")
        self.assertEqual(code, 409)
        self.assertTrue(self.server.approve(offer_id, True))
        code, result = self.request("POST", url, b"hello")
        self.assertEqual(code, 200, result)
        self.assertEqual((Path(self.temp.name) / "photo.txt").read_bytes(), b"hello")
        code, state = self.request("GET", "/api/status?id=" + offer_id)
        self.assertEqual(state["state"], "done")
        self.assertEqual(state["completed"], 1)
        code, _ = self.request("POST", url, b"hello")
        self.assertEqual(code, 409)

    def test_decline(self):
        _, offer = self.request("POST", "/api/offer", {"files": [{"name": "no.txt", "size": 1}]})
        self.server.approve(offer["id"], False)
        code, _ = self.request("POST", "/api/upload?id=" + offer["id"] + "&index=0", b"x")
        self.assertEqual(code, 409)

    def test_filename_and_validation(self):
        self.assertEqual(safe_filename("../CON.txt"), "_CON.txt")
        self.assertEqual(safe_filename("../../okay?.jpg"), "okay_.jpg")
        code, _ = self.request("POST", "/api/offer", {"files": [{"name": "too-big", "size": 3 * 1024 ** 3}]})
        self.assertEqual(code, 201)
        code, _ = self.request("POST", "/api/offer", {"files": []})
        self.assertEqual(code, 400)

    def test_no_configured_file_count_or_total_size_cap(self):
        files = [{"name": f"photo-{i}.mov", "size": 12 * 1024 ** 3} for i in range(150)]
        code, offer = self.request("POST", "/api/offer", {"files": files})
        self.assertEqual(code, 201)
        code, status = self.request("GET", "/api/status?id=" + offer["id"])
        self.assertEqual(code, 200)
        self.assertEqual(status["total"], len(files) * 12 * 1024 ** 3)

    def test_chunked_transfer_and_resume_status(self):
        payload = b"a" * (4 * 1024 * 1024) + b"b" * 5
        _, offer = self.request("POST", "/api/offer", {"files": [{"name": "big.mp4", "size": len(payload)}]})
        offer_id = offer["id"]
        self.server.approve(offer_id, True)
        url = "/api/upload?id=" + offer_id + "&index=0"
        first = payload[:4 * 1024 * 1024]
        code, result = self.request("POST", url + "&offset=0", first)
        self.assertEqual(code, 200)
        self.assertEqual(result["next_offset"], len(first))
        self.assertFalse(result["done"])
        code, status = self.request("GET", "/api/status?id=" + offer_id + "&index=0")
        self.assertEqual(status["file_offset"], len(first))
        code, _ = self.request("POST", url + "&offset=0", b"b")
        self.assertEqual(code, 409)
        code, result = self.request("POST", url + "&offset=" + str(len(first)), payload[len(first):])
        self.assertEqual(code, 200)
        self.assertTrue(result["done"])
        self.assertEqual((Path(self.temp.name) / "big.mp4").read_bytes(), payload)

    def test_empty_file(self):
        _, offer = self.request("POST", "/api/offer", {"files": [{"name": "empty.txt", "size": 0}]})
        self.server.approve(offer["id"], True)
        code, response = self.request("POST", "/api/upload?id=" + offer["id"] + "&index=0&offset=0", b"")
        self.assertEqual(code, 200)
        self.assertTrue(response["done"])
        self.assertEqual((Path(self.temp.name) / "empty.txt").stat().st_size, 0)

    def test_keep_alive_connection_for_successful_requests(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=10)
        try:
            conn.request("GET", "/?k=" + self.server.token)
            first = conn.getresponse()
            self.assertEqual(first.status, 200)
            self.assertEqual(first.getheader("Connection"), "keep-alive")
            first.read()
            original_socket = conn.sock
            self.assertIsNotNone(original_socket)
            conn.request("GET", "/style.css")
            second = conn.getresponse()
            self.assertEqual(second.status, 200)
            second.read()
            self.assertIs(conn.sock, original_socket)
        finally:
            conn.close()

    def test_fast_16_megabyte_chunks(self):
        data = b"z" * (16 * 1024 * 1024) + b"finish"
        _, offer = self.request("POST", "/api/offer", {
            "files": [{"name": "large.bin", "size": len(data)}]
        })
        self.server.approve(offer["id"], True)
        path = "/api/upload?id=" + offer["id"] + "&index=0"
        chunk_size = 16 * 1024 * 1024
        code, result = self.request("POST", path + "&offset=0", data[:chunk_size])
        self.assertEqual(code, 200)
        self.assertEqual(result["next_offset"], chunk_size)
        code, result = self.request("POST", path + "&offset=" + str(chunk_size), data[chunk_size:])
        self.assertEqual(code, 200)
        self.assertTrue(result["done"])
        self.assertEqual((Path(self.temp.name) / "large.bin").read_bytes(), data)

    def test_three_concurrent_files(self):
        data = [bytes([i]) * (1024 * 1024) for i in range(3)]
        _, offer = self.request("POST", "/api/offer", {
            "files": [{"name": f"concurrent-{i}.bin", "size": len(b)} for i, b in enumerate(data)]
        })
        self.server.approve(offer["id"], True)

        def do_upload(i):
            return self.request(
                "POST", "/api/upload?id=" + offer["id"] + "&index=" + str(i), data[i]
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(do_upload, range(3)))
        for code, result in results:
            self.assertEqual(code, 200)
            self.assertTrue(result["done"])
        for i, content in enumerate(data):
            self.assertEqual((Path(self.temp.name) / f"concurrent-{i}.bin").read_bytes(), content)

    def test_no_overwriting(self):
        folder = Path(self.temp.name)
        (folder / "original.txt").write_text("old")
        _, offer = self.request("POST", "/api/offer", {"files": [{"name": "original.txt", "size": 3}]})
        self.server.approve(offer["id"], True)
        code, response = self.request("POST", "/api/upload?id=" + offer["id"] + "&index=0", b"new")
        self.assertEqual(code, 200)
        self.assertEqual(response["saved_as"], "original (1).txt")
        self.assertEqual((folder / "original.txt").read_text(), "old")


if __name__ == "__main__":
    unittest.main()

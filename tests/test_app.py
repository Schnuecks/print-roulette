"""Tests for Print Roulette. Standard library only: python -m unittest"""

import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

import app


class SafeUrlTest(unittest.TestCase):
    def test_accepts_https_on_known_hosts(self):
        for url in (
            "https://makerworld.com/en/models/1-x",
            "https://media.printables.com/media/a.jpg",
            "https://cdn.thingiverse.com/x.png",
        ):
            self.assertEqual(app.safe_url(url), url)

    def test_rejects_everything_else(self):
        for url in (
            None,
            "",
            42,
            "http://makerworld.com/en/models/1-x",  # no https
            "https://evil.example/x",  # unknown host
            "https://makerworld.com.evil.example/x",  # look-alike host
            "javascript:alert(1)",
            "https://makerworld.com/" + "a" * 2000,  # too long
        ):
            self.assertIsNone(app.safe_url(url), url)


class SourceUrlTest(unittest.TestCase):
    def test_only_clean_https_links(self):
        cases = {
            "https://github.com/Schnuecks/print-roulette": "https://github.com/Schnuecks/print-roulette",
            "http://github.com/x": "",
            'https://github.com/x"><script>': "",
            "": "",
        }
        for value, expected in cases.items():
            with mock.patch.object(app, "SOURCE_URL", value):
                self.assertEqual(app.safe_source_url(), expected, value)


class CleanModelTest(unittest.TestCase):
    def test_normalises_and_drops_internal_fields(self):
        model = app.clean_model(
            {
                "id": 7,
                "title": "  A   nice\n model ",
                "creator": " maker ",
                "url": "https://www.printables.com/model/7-a",
                "image": "https://evil.example/i.png",
                "_paid": True,
                "_nsfw": False,
            }
        )
        self.assertEqual(model["title"], "A nice model")
        self.assertEqual(model["creator"], "maker")
        self.assertIsNone(model["image"])  # image on an unknown host is dropped
        self.assertNotIn("_paid", model)
        self.assertNotIn("_nsfw", model)

    def test_rejects_model_link_to_unknown_host(self):
        with self.assertRaises(RuntimeError):
            app.clean_model({"url": "https://evil.example/model"})

    def test_truncates_long_texts(self):
        model = app.clean_model({"url": "https://cults3d.com/en/x", "title": "x" * 500, "creator": "y" * 500})
        self.assertEqual(len(model["title"]), 200)
        self.assertEqual(len(model["creator"]), 80)


class FilterTest(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(app.passes({}, free=True, safe=True))
        self.assertFalse(app.passes({"_paid": True}, free=True, safe=False))
        self.assertTrue(app.passes({"_paid": True}, free=False, safe=False))
        self.assertFalse(app.passes({"_nsfw": True}, free=False, safe=True))
        self.assertTrue(app.passes({"_nsfw": True}, free=False, safe=False))


class SecretTest(unittest.TestCase):
    def test_file_wins_over_variable(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("from-file\n")
        try:
            env = {"TOKEN": "from-env", "TOKEN_FILE": fh.name}
            with mock.patch.dict(os.environ, env):
                self.assertEqual(app.secret("TOKEN"), "from-file")
        finally:
            os.unlink(fh.name)

    def test_variable_and_missing(self):
        with mock.patch.dict(os.environ, {"TOKEN": " v "}, clear=False):
            os.environ.pop("TOKEN_FILE", None)
            self.assertEqual(app.secret("TOKEN"), "v")
        self.assertEqual(app.secret("SURELY_NOT_SET_ANYWHERE"), "")


class RateLimiterTest(unittest.TestCase):
    def test_limit_per_client(self):
        limiter = app.RateLimiter(2)
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))

    def test_window_expires(self):
        limiter = app.RateLimiter(1)
        with mock.patch.object(app.time, "time", return_value=1000.0):
            self.assertTrue(limiter.allow("a"))
            self.assertFalse(limiter.allow("a"))
        with mock.patch.object(app.time, "time", return_value=1061.0):
            self.assertTrue(limiter.allow("a"))


class PublicUrlTest(unittest.TestCase):
    def test_derived_from_headers(self):
        self.assertEqual(app.derive_public_url(None, None, "localhost:8080"), "http://localhost:8080")
        self.assertEqual(
            app.derive_public_url("roulette.example.com", "https", "app:8080"), "https://roulette.example.com"
        )
        self.assertEqual(app.derive_public_url(None, "https", "roulette.example.com"), "https://roulette.example.com")
        self.assertEqual(app.derive_public_url(None, "gopher", "x.example"), "http://x.example")

    def test_forged_host_is_ignored(self):
        for host in ('evil.example"><script>', "a b", "", None, "x" * 300):
            self.assertEqual(app.derive_public_url(None, None, host), "", host)


class ServerTest(unittest.TestCase):
    """Starts the real handler on a free port."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    def test_healthz(self):
        resp, body = self.get("/healthz")
        self.assertEqual((resp.status, body), (200, b"ok"))

    def test_sources(self):
        resp, body = self.get("/api/sources")
        self.assertEqual(resp.status, 200)
        self.assertEqual([s["key"] for s in json.loads(body)], ["makerworld", "printables", "cults", "thingiverse"])

    def test_unknown_source(self):
        resp, body = self.get("/api/random?source=nope")
        self.assertEqual(resp.status, 404)
        self.assertEqual(json.loads(body)["code"], "unknown_source")

    def test_security_headers(self):
        resp, _ = self.get("/")
        self.assertIn("default-src 'none'", resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")

    def test_index_uses_request_host_without_public_url(self):
        with mock.patch.object(app, "PUBLIC_URL", ""):
            _, body = self.get("/", {"Host": "roulette.example.com", "X-Forwarded-Proto": "https"})
        self.assertIn(b'content="https://roulette.example.com/og.png"', body)
        self.assertNotIn(b"__PUBLIC_URL__", body)

    def test_index_uses_public_url_when_set(self):
        with mock.patch.object(app, "PUBLIC_URL", "https://fixed.example"):
            _, body = self.get("/", {"Host": "other.example"})
        self.assertIn(b'content="https://fixed.example/og.png"', body)

    def test_static_path_traversal_and_types(self):
        for path in ("/../app.py", "/%2e%2e/app.py", "/static/../../etc/passwd", "/fonts/OFL-manrope.txt%00.js"):
            resp, _ = self.get(path)
            self.assertEqual(resp.status, 404, path)
        resp, _ = self.get("/style.css")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.getheader("Content-Type").startswith("text/css"))


if __name__ == "__main__":
    unittest.main()

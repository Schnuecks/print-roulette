"""Tests for Print Roulette. Standard library only: python -m unittest"""

import http.client
import json
import os
import tempfile
import threading
import unittest
import urllib.error
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
        with mock.patch.object(app, "PUBLIC_URL", ""), mock.patch.object(app, "TRUST_PROXY", True):
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

    def test_index_is_private_without_public_url(self):
        with mock.patch.object(app, "PUBLIC_URL", ""):
            resp, _ = self.get("/")
        self.assertTrue(resp.getheader("Cache-Control").startswith("private"))
        with mock.patch.object(app, "PUBLIC_URL", "https://fixed.example"):
            resp, _ = self.get("/")
        self.assertTrue(resp.getheader("Cache-Control").startswith("public"))

    def test_busy_when_all_roll_slots_are_taken(self):
        slots = threading.BoundedSemaphore(1)
        slots.acquire()
        with mock.patch.object(app, "ROLL_SLOTS", slots):
            resp, body = self.get("/api/random?source=makerworld")
        self.assertEqual(resp.status, 503)
        self.assertEqual(json.loads(body)["code"], "busy")


class ContentSecurityPolicyTest(unittest.TestCase):
    def directive(self, name):
        csp = app.SECURITY_HEADERS["Content-Security-Policy"]
        parts = [p.strip().split() for p in csp.split(";") if p.strip()]
        return next(p[1:] for p in parts if p[0] == name)

    def test_img_src_has_no_wildcard(self):
        sources = self.directive("img-src")
        self.assertNotIn("https:", sources)
        self.assertNotIn("*", " ".join(sources))

    def test_every_image_host_is_allowed_in_img_src(self):
        sources = self.directive("img-src")
        for host in app.IMAGE_HOSTS:
            self.assertIn(f"https://{host}", sources)
            self.assertEqual(app.safe_url(f"https://{host}/x.png"), f"https://{host}/x.png")

    def test_embedder_policy(self):
        self.assertEqual(app.SECURITY_HEADERS["Cross-Origin-Embedder-Policy"], "credentialless")


class ClientAddressTest(unittest.TestCase):
    def client(self, xff, trust=True, hops=1, remote="192.0.2.1"):
        handler = app.Handler.__new__(app.Handler)
        handler.headers = {"X-Forwarded-For": xff} if xff is not None else {}
        handler.client_address = (remote, 12345)
        with mock.patch.object(app, "TRUST_PROXY", trust), mock.patch.object(app, "TRUSTED_PROXY_HOPS", hops):
            return handler.client()

    def test_last_entry_is_used(self):
        # The client may put anything in front; the proxy appends the real address at the end
        self.assertEqual(self.client("1.1.1.1, 203.0.113.9"), "203.0.113.9")
        self.assertEqual(self.client("9.9.9.9, 203.0.113.9"), "203.0.113.9")

    def test_spoofed_front_entries_count_as_one_client(self):
        limiter = app.RateLimiter(2)
        clients = [self.client(f"10.0.0.{i}, 203.0.113.9") for i in range(3)]
        self.assertEqual([limiter.allow(c) for c in clients], [True, True, False])

    def test_hops_from_the_end(self):
        self.assertEqual(self.client("6.6.6.6, 203.0.113.9, 10.0.0.2", hops=2), "203.0.113.9")
        self.assertEqual(self.client("203.0.113.9", hops=2), "192.0.2.1")  # too few entries

    def test_header_ignored_without_trust(self):
        self.assertEqual(self.client("203.0.113.9", trust=False), "192.0.2.1")
        self.assertEqual(self.client(None), "192.0.2.1")


class CultsRefillTest(unittest.TestCase):
    def make(self):
        cults = app.Cults.__new__(app.Cults)
        cults.user, cults.apikey, cults.enabled = "u", "k", True
        cults.lock = threading.Lock()
        cults.fill_lock = threading.Lock()
        cults.pools = {False: [], True: []}
        cults.used = {False: [], True: []}
        cults.last_call = 0.0
        cults.paused_until = 0.0
        return cults

    def test_failure_pauses_refills(self):
        cults = self.make()
        calls = []

        def failing_fill(free):
            calls.append(free)
            cults.last_call = app.time.time()
            raise RuntimeError("api down")

        cults.fill = failing_fill
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                cults.random()
        self.assertEqual(len(calls), 1)  # pause after the error, no new calls
        self.assertGreater(cults.paused_until, app.time.time())

    def test_empty_pool_is_not_refilled_on_every_request(self):
        cults = self.make()
        calls = []

        def empty_fill(free):
            calls.append(free)
            cults.last_call = app.time.time()
            return 0

        cults.fill = empty_fill
        for _ in range(3):
            with self.assertRaises(RuntimeError):
                cults.random()
        self.assertEqual(len(calls), 3)  # one roll tries three weeks, the next ones wait

    def test_only_one_refill_at_a_time(self):
        cults = self.make()
        cults.fill_lock.acquire()  # another request is refilling
        cults.fill = mock.Mock(side_effect=AssertionError("must not refill"))
        with self.assertRaises(RuntimeError):
            cults.random()
        cults.fill.assert_not_called()

    def test_shown_models_do_not_repeat_until_the_pool_is_used_up(self):
        cults = self.make()
        cults.last_call = app.time.time()  # no refill during the test
        cults.pools[False] = [{"url": f"https://cults3d.com/en/{i}"} for i in range(5)]
        urls = [cults.random()["url"] for _ in range(5)]
        self.assertEqual(len(set(urls)), 5)
        self.assertEqual(cults.pools[False], [])
        self.assertIn(cults.random()["url"], urls)  # nothing new left: an older one instead of an error

    def test_fill_reads_all_weeks_and_skips_known_models(self):
        cults = self.make()
        cults.used[False] = [{"url": "https://cults3d.com/en/old"}]

        def week(*names):
            return {"results": [{"name": n, "url": f"https://cults3d.com/en/{n}", "safe": True} for n in names]}

        answer = {"data": {"w0": week("a", "b"), "w1": week("old"), "w2": None, "w3": week("c"), "w4": week()}}
        with mock.patch.object(app, "http", return_value=json.dumps(answer)) as fake:
            cults.fill(False)
        variables = fake.call_args.args[1]["variables"]
        self.assertEqual(len([k for k in variables if k.startswith("a")]), app.Cults.WEEKS)
        self.assertEqual([m["title"] for m in cults.pools[False]], ["a", "b", "c"])


class MakerWorldTest(unittest.TestCase):
    API_ANSWER = {
        "id": 42,
        "title": "原名",
        "titleTranslated": "Nice model",
        "coverUrl": "https://makerworld.bblmw.com/makerworld/model/x.jpg",
        "designCreator": {"name": "maker"},
        "nsfw": False,
        "paidSetting": {"isPaid": False},
        "isPointRedeemable": False,
    }

    def make(self, answers):
        """MakerWorld with one sitemap page holding model 42; answers are returned by the API in turn."""
        mw = app.MakerWorld()
        mw.sitemap_pages = lambda: ["page"]
        mw.models_from_page = lambda url: [(42, "nice-model")]

        def fake_http(url, *args, **kwargs):
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return json.dumps(answer)

        return mw, mock.patch.object(app, "http", side_effect=fake_http)

    def test_details_from_the_api(self):
        mw, patch = self.make([self.API_ANSWER])
        with patch:
            model = app.clean_model(mw.random())
        self.assertEqual(model["title"], "Nice model")
        self.assertEqual(model["creator"], "maker")
        self.assertEqual(model["image"], self.API_ANSWER["coverUrl"])
        self.assertEqual(model["url"], f"https://makerworld.com/{mw.LANG}/models/42-nice-model")

    def test_filters_apply(self):
        paid = {**self.API_ANSWER, "paidSetting": {"isPaid": True}}
        nsfw = {**self.API_ANSWER, "nsfw": True}
        gone = urllib.error.HTTPError("u", 404, "not found", None, None)
        mw, patch = self.make([paid, nsfw, gone, self.API_ANSWER])
        with patch:
            model = mw.random(free=True, safe=True)
        self.assertFalse(model["_paid"] or model["_nsfw"])

    def test_api_failure(self):
        down = urllib.error.URLError("down")
        mw, patch = self.make([down, down])
        with patch:
            with self.assertRaises(urllib.error.URLError):
                mw.random(free=False, safe=True)  # filters on: no unchecked model
            model = mw.random(free=False, safe=False)  # filters off: the link from the sitemap is enough
        self.assertEqual(model["title"], "Nice Model")
        self.assertIsNone(model["image"])


if __name__ == "__main__":
    unittest.main()

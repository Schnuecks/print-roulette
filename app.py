"""Print Roulette: random 3D models from MakerWorld, Printables, Cults3D and Thingiverse."""

import base64
import json
import logging
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

__version__ = "0.5.2"

PORT = int(os.environ.get("PORT", "8080"))
STATIC_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))
DAY = 24 * 3600
MAX_BODY = 8 * 1024 * 1024  # largest expected response (a sitemap page is about 1.3 MB)
RATE_PER_MINUTE = int(os.environ.get("RATE_PER_MINUTE", "30"))  # rolls per IP and minute
TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"  # use X-Forwarded-* from the reverse proxy
# How many trusted proxies stand in front of the app; the client address is that many entries
# from the end of X-Forwarded-For (the front entries are chosen by the client and not trusted)
TRUSTED_PROXY_HOPS = max(1, int(os.environ.get("TRUSTED_PROXY_HOPS", "1")))
# Rolls handled at the same time; further requests get "busy" right away instead of piling up
MAX_ROLLS = max(1, int(os.environ.get("MAX_ROLLS", "8")))
UPSTREAM_TIMEOUT = 8  # seconds per request to a platform
ROLL_DEADLINE = 20  # seconds for all attempts of one roll
# Public address for link previews; empty means: derive it from the request (Host header)
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
# Link to the source code in the footer (AGPL); empty hides it
SOURCE_URL = os.environ.get("SOURCE_URL", "https://github.com/Schnuecks/print-roulette").strip()
# Honest user agent: points to this instance if PUBLIC_URL is set, otherwise to the project
UA = os.environ.get(
    "USER_AGENT", f"PrintRoulette/{__version__} (+{PUBLIC_URL or 'https://github.com/Schnuecks/print-roulette'})"
)

log = logging.getLogger("roulette")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Links and images sent to the browser may only point to these hosts
# Hosts that preview images come from; the CSP allows images only from these
IMAGE_HOSTS = (
    "makerworld.bblmw.com",
    "media.printables.com",
    "images.cults3d.com",
    "fbi.cults3d.com",
    "cdn.thingiverse.com",
    "resize.thingiverse.com",
)
# Hosts of the model pages the result links to
LINK_HOSTS = (
    "makerworld.com",
    "www.printables.com",
    "cults3d.com",
    "www.thingiverse.com",
)
ALLOWED_HOSTS = frozenset(IMAGE_HOSTS + LINK_HOSTS)


def safe_url(url):
    """Return the URL if it uses https and points to a known host, otherwise None."""
    if not url or not isinstance(url, str) or len(url) > 2000:
        return None
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        return None
    return url


def safe_source_url():
    """Only https links go into the footer; anything else hides the link."""
    parts = urllib.parse.urlsplit(SOURCE_URL) if SOURCE_URL else None
    if not parts or parts.scheme != "https" or not parts.hostname or '"' in SOURCE_URL or "<" in SOURCE_URL:
        return ""
    return SOURCE_URL


def clean_model(model):
    """Normalise and check what is sent to the browser."""
    url = safe_url(model.get("url"))
    if not url:
        raise RuntimeError("Model link points to an unexpected host")
    title = re.sub(r"\s+", " ", str(model.get("title") or "")).strip()[:200] or ""
    creator = model.get("creator")
    creator = re.sub(r"\s+", " ", str(creator)).strip()[:80] if creator else None
    return {
        "id": str(model.get("id", ""))[:80],
        "title": title,
        "creator": creator,
        "url": url,
        "image": safe_url(model.get("image")),
    }


HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}(:[0-9]{1,5})?$")


def derive_public_url(forwarded_host, forwarded_proto, host):
    """Build the public base URL from request headers; only plain host names are accepted.

    Falls back to a relative URL ("") if nothing usable is sent, so a forged Host header can
    never put foreign markup into the page."""
    candidate = (forwarded_host or host or "").split(",")[0].strip()
    if not HOST_RE.match(candidate):
        return ""
    # The app itself speaks plain HTTP; behind a proxy X-Forwarded-Proto tells the real scheme
    proto = (forwarded_proto or "").split(",")[0].strip().lower()
    if proto not in ("http", "https"):
        proto = "http"
    return f"{proto}://{candidate}"


def secret(name):
    """Read NAME, or the file named in NAME_FILE."""
    path = os.environ.get(name + "_FILE")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    return os.environ.get(name, "").strip()


def http(url, data=None, headers=None, timeout=UPSTREAM_TIMEOUT):
    hdrs = {"User-Agent": UA, "Accept": "application/json, application/xml, text/xml"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    if not url.startswith("https://"):
        raise ValueError("Only https is allowed")
    req = urllib.request.Request(url, data=body, headers=hdrs)  # noqa: S310 - fixed https hosts
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise RuntimeError(f"Response from {urllib.parse.urlsplit(url).hostname} is too large")
    return raw.decode("utf-8", "replace")


def slug_title(slug):
    return re.sub(r"[-_]+", " ", slug).strip().title()


class Source:
    key = ""
    name = ""
    color = ""
    enabled = True
    reason = ""
    # Which filters the source can check
    can_free = False
    can_nsfw = False

    def info(self):
        return {
            "key": self.key,
            "name": self.name,
            "color": self.color,
            "enabled": self.enabled,
            "reason": self.reason,
            "filters": {"free": self.can_free, "nsfw": self.can_nsfw},
        }

    def random(self, free=False, safe=True):
        raise NotImplementedError


def passes(model, free, safe):
    """Apply the filters using the internal fields _paid and _nsfw."""
    if free and model.get("_paid"):
        return False
    return not (safe and model.get("_nsfw"))


# ---------------------------------------------------------------- MakerWorld


class MakerWorld(Source):
    """Rolls a model from the public sitemaps, then asks the model API for image, creator and flags."""

    key, name, color = "makerworld", "MakerWorld", "#00AE42"
    can_free = can_nsfw = True
    BASE = "https://makerworld.com"
    API = "https://makerworld.com/api/v1/design-service/design/%d"
    LANG = os.environ.get("MW_LANG", "en")
    LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
    attempts = 6

    def __init__(self):
        self.lock = threading.Lock()
        self.pages, self.fetched = [], 0.0
        self.cache = OrderedDict()
        self.model_re = re.compile(re.escape(self.BASE) + "/" + self.LANG + r"/models/(\d+)-([^<]+)")

    def sitemap_pages(self):
        with self.lock:
            if self.pages and time.time() - self.fetched < DAY:
                return self.pages
        pages = [u for u in self.LOC_RE.findall(http(f"{self.BASE}/sitemaps/index.xml")) if "/sitemaps/models.xml" in u]
        if not pages:
            raise RuntimeError("Sitemap index contains no model pages")
        with self.lock:
            self.pages, self.fetched = pages, time.time()
        return pages

    def models_from_page(self, url):
        with self.lock:
            if url in self.cache:
                self.cache.move_to_end(url)
                return self.cache[url]
        models = [(int(i), s) for i, s in self.model_re.findall(http(url))]
        with self.lock:
            self.cache[url] = models
            while len(self.cache) > 16:
                self.cache.popitem(last=False)
        return models

    def details(self, mid, slug):
        """Return the model dict, or None if the model is gone."""
        try:
            data = json.loads(http(self.API % mid))
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                return None
            raise
        if not data.get("id"):
            return None
        return {
            "id": str(mid),
            "title": data.get("titleTranslated") or data.get("title") or slug_title(slug),
            "image": data.get("coverUrl"),
            "creator": (data.get("designCreator") or {}).get("name"),
            "url": f"{self.BASE}/{self.LANG}/models/{mid}-{slug}",
            "_nsfw": bool(data.get("nsfw")),
            "_paid": bool((data.get("paidSetting") or {}).get("isPaid")) or bool(data.get("isPointRedeemable")),
        }

    def random(self, free=False, safe=True):
        pages = self.sitemap_pages()
        deadline = time.monotonic() + ROLL_DEADLINE
        for _ in range(self.attempts):
            if time.monotonic() > deadline:
                break
            models = self.models_from_page(random.choice(pages))
            if not models:
                continue
            mid, slug = random.choice(models)
            try:
                model = self.details(mid, slug)
            except Exception:
                # Without the API the filters cannot be checked; without filters the link is enough
                if free or safe:
                    raise
                return {
                    "id": str(mid),
                    "title": slug_title(slug),
                    "image": None,
                    "creator": None,
                    "url": f"{self.BASE}/{self.LANG}/models/{mid}-{slug}",
                }
            if model and passes(model, free, safe):
                return model
        raise RuntimeError("No matching model found after several attempts")


# --------------------------------------------- random ID below an upper bound


class RandomIdSource(Source):
    """Rolls IDs below an upper bound that is probed upwards once a day."""

    start_max = 1
    step = 1
    attempts = 12

    def __init__(self):
        self.lock = threading.Lock()
        self.max_id = int(os.environ.get(self.key.upper() + "_MAX_ID", self.start_max))
        self.probed = 0.0

    def exists(self, mid):
        """Return the model dict, or None if the ID does not exist."""
        raise NotImplementedError

    def probe_max(self):
        hi = self.max_id
        # probe upwards while there are hits (at most 20 steps)
        for _ in range(20):
            cand = hi + self.step
            found = any(self.exists(cand - random.randint(0, self.step // 10 or 1)) for _ in range(3))
            if not found:
                break
            hi = cand
        with self.lock:
            self.max_id = max(self.max_id, hi)

    def probe_in_background(self):
        """Probe the upper bound at most once a day, without delaying the roll."""
        with self.lock:
            if time.time() - self.probed < DAY:
                return
            self.probed = time.time()

        def run():
            try:
                self.probe_max()
            except Exception as exc:
                log.warning("%s: upper bound not probed: %s", self.key, exc)

        threading.Thread(target=run, name=f"probe-{self.key}", daemon=True).start()

    def random(self, free=False, safe=True):
        self.probe_in_background()
        deadline = time.monotonic() + ROLL_DEADLINE
        for _ in range(self.attempts):
            if time.monotonic() > deadline:
                break
            model = self.exists(random.randint(1, self.max_id))
            if model and passes(model, free, safe):
                return model
        raise RuntimeError("No matching model found after several attempts")


class Printables(RandomIdSource):
    key, name, color = "printables", "Printables", "#FA6831"
    can_free = can_nsfw = True
    start_max, step = 1_800_000, 20_000
    API = "https://api.printables.com/graphql/"
    QUERY = '{ print(id: "%d") { id name slug nsfw price premium image { filePath } user { publicUsername } } }'

    def exists(self, mid):
        data = json.loads(http(self.API, {"query": self.QUERY % mid})).get("data", {}).get("print")
        if not data:
            return None
        img = data.get("image") or {}
        image = None
        if img.get("filePath"):
            image = "https://media.printables.com/" + img["filePath"]
        return {
            "id": data["id"],
            "title": data["name"],
            "image": image,
            "creator": (data.get("user") or {}).get("publicUsername"),
            "url": f"https://www.printables.com/model/{data['id']}-{data['slug']}",
            "_nsfw": bool(data.get("nsfw")),
            "_paid": bool(data.get("price")) or bool(data.get("premium")),
        }


class Thingiverse(RandomIdSource):
    key, name, color = "thingiverse", "Thingiverse", "#248BFB"
    can_free = can_nsfw = True  # everything on Thingiverse is free
    start_max, step = 7_000_000, 50_000
    API = "https://api.thingiverse.com"

    def __init__(self):
        super().__init__()
        self.token = secret("THINGIVERSE_TOKEN")
        if not self.token:
            self.enabled, self.reason = False, "No API token (THINGIVERSE_TOKEN) configured"

    def exists(self, mid):
        try:
            raw = http(f"{self.API}/things/{mid}", headers={"Authorization": f"Bearer {self.token}"})
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                return None
            raise
        data = json.loads(raw)
        if not data.get("public_url"):
            return None
        return {
            "id": str(data["id"]),
            "title": data["name"],
            "image": data.get("thumbnail"),
            "creator": (data.get("creator") or {}).get("name"),
            "url": data["public_url"],
            "_nsfw": bool(data.get("is_nsfw")),
            "_paid": False,
        }


# -------------------------------------------------------------------- Cults3D


def weeks_query(weeks, per_week, fields):
    """One GraphQL query with a creationsBatch for each week, named w0, w1, …"""
    params = ", ".join(f"$a{i}: ISO8601DateTime, $b{i}: ISO8601DateTime" for i in range(weeks))
    batches = " ".join(
        f"w{i}: creationsBatch(limit: {per_week}, offset: 0, onlyFree: $free, "
        f"submittedAfter: $a{i}, submittedBefore: $b{i}) {{ results {{ {fields} }} }}"
        for i in range(weeks)
    )
    return f"query($free: Boolean, {params}) {{ {batches} }}"


class Cults(Source):
    """Official API. Rolls several random weeks since 2014 in one call and keeps the results in a
    pool; a model leaves the pool once it was shown, so rolls in a row do not repeat."""

    key, name, color = "cults", "Cults3D", "#822EF5"
    can_free = can_nsfw = True
    API = "https://cults3d.com/graphql"
    WEEKS = 5  # weeks per API call; one week alone is often a series by the same creator
    PER_WEEK = 10
    FIELDS = (
        "name(locale: EN) url(locale: EN) illustrationImageUrl safe price(currency: EUR) { cents } creator { nick }"
    )
    QUERY = weeks_query(WEEKS, PER_WEEK, FIELDS)
    START = 1388534400  # 2014-01-01, launch of Cults
    WINDOW = 7 * DAY
    POOL_MAX = 500
    MIN_INTERVAL = 180  # seconds between two API calls, keeps well below the daily limit (about 500)
    EMPTY_INTERVAL = 15  # an empty pool may be refilled sooner, but not on every request
    BACKOFF = 120  # pause after a failed API call

    def __init__(self):
        self.user, self.apikey = secret("CULTS_USER"), secret("CULTS_API_KEY")
        if not (self.user and self.apikey):
            self.enabled, self.reason = False, "No API key (CULTS_USER / CULTS_API_KEY) configured"
        self.lock = threading.Lock()
        self.pools = {False: [], True: []}  # not shown yet; key: free models only?
        self.used = {False: [], True: []}  # already shown, used again only when nothing new is left
        self.last_call = 0.0
        self.paused_until = 0.0
        self.fill_lock = threading.Lock()  # only one refill at a time

    def fill(self, free):
        auth = base64.b64encode(f"{self.user}:{self.apikey}".encode()).decode()
        iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731
        variables = {"free": free}
        for i in range(self.WEEKS):
            after = random.randint(self.START, int(time.time()) - self.WINDOW)
            variables[f"a{i}"], variables[f"b{i}"] = iso(after), iso(after + self.WINDOW)
        with self.lock:
            self.last_call = time.time()
        raw = http(self.API, {"query": self.QUERY, "variables": variables}, headers={"Authorization": f"Basic {auth}"})
        data = json.loads(raw)
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "Cults API error"))
        items = [c for week in (data.get("data") or {}).values() for c in ((week or {}).get("results") or [])]
        batch = [
            {
                "id": c["url"].rstrip("/").rsplit("/", 1)[-1],
                "title": c["name"],
                "image": c.get("illustrationImageUrl"),
                "creator": (c.get("creator") or {}).get("nick"),
                "url": c["url"],
                "_nsfw": not c.get("safe", True),
                "_paid": bool((c.get("price") or {}).get("cents")),
            }
            for c in items
            if c.get("url")
        ]
        with self.lock:
            pool = self.pools[free]
            known = {m["url"] for m in pool + self.used[free]}
            pool.extend(m for m in batch if m["url"] not in known)
            del pool[: max(0, len(pool) - self.POOL_MAX)]
        return len(batch)

    def candidates(self, free, safe, used=False):
        with self.lock:
            return [m for m in (self.used if used else self.pools)[free] if passes(m, free, safe)]

    def take(self, free, safe):
        """Draw a model that was not shown yet and move it to the used ones; when nothing new is
        left, an already shown model is better than an error."""
        with self.lock:
            pool, used = self.pools[free], self.used[free]
            fresh = [i for i, m in enumerate(pool) if passes(m, free, safe)]
            if fresh:
                model = pool.pop(random.choice(fresh))
                used.append(model)
                del used[: max(0, len(used) - self.POOL_MAX)]
                return dict(model)
            old = [m for m in used if passes(m, free, safe)]
            return dict(random.choice(old)) if old else None

    def random(self, free=False, safe=True):
        known = self.candidates(free, safe) or self.candidates(free, safe, used=True)
        now = time.time()
        with self.lock:
            since = now - self.last_call
            paused = now < self.paused_until
        # Refill when nothing is known yet (not more often than EMPTY_INTERVAL) or MIN_INTERVAL
        # has passed. Never during a pause after an error, and only one request refills at a
        # time; the others use the pool or get "unavailable". Empty weeks (early years) are
        # rolled again up to three times.
        if paused:
            tries = 0
        elif not known:
            tries = 3 if since > self.EMPTY_INTERVAL else 0
        else:
            tries = 1 if since > self.MIN_INTERVAL else 0
        if tries and self.fill_lock.acquire(blocking=False):
            try:
                for _ in range(tries):
                    self.fill(free)
                    if self.candidates(free, safe):
                        break
            except Exception as exc:
                with self.lock:
                    self.paused_until = time.time() + self.BACKOFF
                log.warning("cults: refill failed, pausing %ss: %s", self.BACKOFF, exc)
            finally:
                self.fill_lock.release()
        model = self.take(free, safe)
        if not model:
            raise RuntimeError("No matching model in the pool")
        return model


SOURCES = OrderedDict((s.key, s) for s in (MakerWorld(), Printables(), Cults(), Thingiverse()))


# ----------------------------------------------------------------- rate limit


class RateLimiter:
    """Simple window per client: at most N rolls per minute."""

    def __init__(self, per_minute):
        self.per_minute = per_minute
        self.lock = threading.Lock()
        self.hits = {}

    def allow(self, client):
        now = time.time()
        with self.lock:
            if len(self.hits) > 10_000:  # limit memory
                self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > now - 60}
            times = [t for t in self.hits.get(client, []) if t > now - 60]
            if len(times) >= self.per_minute:
                self.hits[client] = times
                return False
            times.append(now)
            self.hits[client] = times
            return True


LIMITER = RateLimiter(RATE_PER_MINUTE)
ROLL_SLOTS = threading.BoundedSemaphore(MAX_ROLLS)

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' " + " ".join(f"https://{h}" for h in IMAGE_HOSTS) + "; "
    "font-src 'self'; connect-src 'self'; manifest-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # credentialless instead of require-corp: the preview images come from foreign hosts that
    # send no Cross-Origin-Resource-Policy header and would not load with require-corp
    "Cross-Origin-Embedder-Policy": "credentialless",
}


# --------------------------------------------------------------------- server


class Handler(BaseHTTPRequestHandler):
    server_version = "PrintRoulette"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    def client(self):
        """Client address for the rate limit. Behind TRUSTED_PROXY_HOPS proxies it is that many
        entries from the end of X-Forwarded-For; entries further to the front come from the
        client and could be chosen freely."""
        if TRUST_PROXY:
            hops = [h.strip() for h in self.headers.get("X-Forwarded-For", "").split(",") if h.strip()]
            if len(hops) >= TRUSTED_PROXY_HOPS:
                return hops[-TRUSTED_PROXY_HOPS][:64]
        return self.client_address[0]

    def public_url(self):
        """PUBLIC_URL, or the address the page was requested under (for link previews)."""
        if PUBLIC_URL:
            return PUBLIC_URL
        return derive_public_url(
            self.headers.get("X-Forwarded-Host") if TRUST_PROXY else None,
            self.headers.get("X-Forwarded-Proto") if TRUST_PROXY else None,
            self.headers.get("Host"),
        )

    def _send(self, code, body, ctype, cache="no-store", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        for k, v in {**SECURITY_HEADERS, **(extra or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj, extra=None):
        self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8", extra=extra)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path, _, query = self.path.partition("?")
        path = urllib.parse.unquote(path)
        if path == "/api/sources":
            self._json(200, [s.info() for s in SOURCES.values()])
            return
        if path == "/api/random":
            params = urllib.parse.parse_qs(query, max_num_fields=5)
            src = SOURCES.get((params.get("source") or ["makerworld"])[0])
            # Errors carry a code that the page translates into the chosen language
            if not src:
                self._json(404, {"code": "unknown_source", "error": "Unknown platform"})
                return
            if not src.enabled:
                self._json(503, {"code": "not_configured", "error": src.reason})
                return
            if not LIMITER.allow(self.client()):
                self._json(429, {"code": "rate_limit", "error": "Too many rolls"}, extra={"Retry-After": "60"})
                return
            free = (params.get("free") or ["0"])[0] == "1"
            safe = (params.get("nsfw") or ["0"])[0] != "1"
            if not ROLL_SLOTS.acquire(blocking=False):
                self._json(
                    503, {"code": "busy", "error": "Too many rolls at the same time"}, extra={"Retry-After": "5"}
                )
                return
            try:
                model = clean_model(src.random(free=free, safe=safe))
                model.update({"source": src.key, "sourceName": src.name, "color": src.color})
                self._json(200, model)
            except Exception as exc:
                log.warning("%s: %s", src.key, exc)
                self._json(502, {"code": "unavailable", "error": f"{src.name} is not responding"})
            finally:
                ROLL_SLOTS.release()
            return
        if path == "/healthz":
            self._send(200, b"ok", "text/plain")
            return
        if path == "/":
            path = "/index.html"
        if "\x00" in path or ".." in path or "\\" in path:
            self._send(404, b"not found", "text/plain")
            return
        file = os.path.realpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not file.startswith(STATIC_DIR + os.sep) or not os.path.isfile(file):
            self._send(404, b"not found", "text/plain")
            return
        # Fixed list instead of guessing from the path: only known file types are served
        ctype = STATIC_TYPES.get(os.path.splitext(file)[1].lower())
        if not ctype:
            self._send(404, b"not found", "text/plain")
            return
        with open(file, "rb") as fh:
            body = fh.read()
        if file.endswith(".html"):
            # The regex runs on the static file only; values from the request are inserted afterwards
            if safe_source_url():
                body = body.replace(b"__SOURCE_URL__", safe_source_url().encode())
            else:
                body = re.sub(rb"<!--source-->.*?<!--/source-->", b"", body, flags=re.S)
            body = body.replace(b"__PUBLIC_URL__", self.public_url().encode())
        # Without PUBLIC_URL the page contains the requested host, so shared caches must not keep it
        cache = "private, max-age=300" if file.endswith(".html") and not PUBLIC_URL else "public, max-age=300"
        self._send(200, body, ctype, cache)


if __name__ == "__main__":
    if "--version" in sys.argv:
        print(__version__)
        raise SystemExit(0)
    active = ", ".join(s.name for s in SOURCES.values() if s.enabled)
    log.info("Print Roulette listening on port %s; active sources: %s", PORT, active)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

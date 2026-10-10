"""Print Roulette: zufällige 3D-Modelle von MakerWorld, Printables, Cults3D und Thingiverse."""

import base64
import json
import logging
import mimetypes
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

__version__ = "0.2.0"

PORT = int(os.environ.get("PORT", "8080"))
UA = os.environ.get("USER_AGENT", f"PrintRoulette/{__version__} (+https://roulette.hessis.eu)")
STATIC_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))
DAY = 24 * 3600
MAX_BODY = 8 * 1024 * 1024  # größte erwartete Antwort (Sitemap-Seite ≈ 1,3 MB)
RATE_PER_MINUTE = int(os.environ.get("RATE_PER_MINUTE", "30"))  # Würfe pro IP und Minute
TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") == "1"  # X-Forwarded-For von Traefik
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://roulette.hessis.eu").rstrip("/")  # für Vorschau-Links

log = logging.getLogger("roulette")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Nur zu diesen Hosts dürfen Links und Bilder zeigen, die an den Browser gehen
ALLOWED_HOSTS = {
    "makerworld.com",
    "www.printables.com",
    "media.printables.com",
    "cults3d.com",
    "images.cults3d.com",
    "fbi.cults3d.com",
    "www.thingiverse.com",
    "cdn.thingiverse.com",
    "resize.thingiverse.com",
}


def safe_url(url):
    """Gibt die URL zurück, wenn sie https ist und auf einen bekannten Host zeigt, sonst None."""
    if not url or not isinstance(url, str) or len(url) > 2000:
        return None
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        return None
    return url


def clean_model(model):
    """Vereinheitlicht und prüft, was an den Browser geht."""
    url = safe_url(model.get("url"))
    if not url:
        raise RuntimeError("Modell-Link zeigt auf unerwarteten Host")
    title = re.sub(r"\s+", " ", str(model.get("title") or "")).strip()[:200] or "Ohne Titel"
    creator = model.get("creator")
    creator = re.sub(r"\s+", " ", str(creator)).strip()[:80] if creator else None
    return {
        "id": str(model.get("id", ""))[:80],
        "title": title,
        "creator": creator,
        "url": url,
        "image": safe_url(model.get("image")),
    }


def secret(name):
    """Liest NAME oder die Datei aus NAME_FILE."""
    path = os.environ.get(name + "_FILE")
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    return os.environ.get(name, "").strip()


def http(url, data=None, headers=None, timeout=20):
    hdrs = {"User-Agent": UA, "Accept": "application/json, application/xml, text/xml"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    if not url.startswith("https://"):
        raise ValueError("Nur https erlaubt")
    req = urllib.request.Request(url, data=body, headers=hdrs)  # noqa: S310 - feste https-Hosts
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        raw = resp.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise RuntimeError(f"Antwort von {urllib.parse.urlsplit(url).hostname} zu groß")
    return raw.decode("utf-8", "replace")


def slug_title(slug):
    return re.sub(r"[-_]+", " ", slug).strip().title()


class Source:
    key = ""
    name = ""
    color = ""
    enabled = True
    reason = ""
    # Welche Filter die Quelle prüfen kann
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
    """Prüft die Filter anhand der internen Felder _paid und _nsfw."""
    if free and model.get("_paid"):
        return False
    return not (safe and model.get("_nsfw"))


# ---------------------------------------------------------------- MakerWorld


class MakerWorld(Source):
    key, name, color = "makerworld", "MakerWorld", "#00AE42"
    BASE = "https://makerworld.com"
    LANG = os.environ.get("MW_LANG", "en")
    LOC_RE = re.compile(r"<loc>([^<]+)</loc>")

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
            raise RuntimeError("Sitemap-Index enthält keine Modellseiten")
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

    def random(self, free=False, safe=True):
        # Die Sitemap kennt weder Preis noch NSFW-Kennzeichen, Filter greifen hier nicht
        pages = self.sitemap_pages()
        for _ in range(3):
            models = self.models_from_page(random.choice(pages))
            if models:
                mid, slug = random.choice(models)
                return {
                    "id": str(mid),
                    "title": slug_title(slug),
                    "image": None,
                    "creator": None,
                    "url": f"{self.BASE}/{self.LANG}/models/{mid}-{slug}",
                }
        raise RuntimeError("Keine Modelle in den geladenen Sitemap-Seiten")


# ------------------------------------------------- Zufalls-ID mit Obergrenze


class RandomIdSource(Source):
    """Würfelt IDs bis zu einer Obergrenze, die täglich nach oben getastet wird."""

    start_max = 1
    step = 1
    attempts = 12

    def __init__(self):
        self.lock = threading.Lock()
        self.max_id = int(os.environ.get(self.key.upper() + "_MAX_ID", self.start_max))
        self.probed = 0.0

    def exists(self, mid):
        """Gibt das Modell-Dict zurück oder None, wenn es die ID nicht gibt."""
        raise NotImplementedError

    def probe_max(self):
        hi = self.max_id
        # nach oben tasten, solange Treffer kommen (max. 20 Schritte)
        for _ in range(20):
            cand = hi + self.step
            found = any(self.exists(cand - random.randint(0, self.step // 10 or 1)) for _ in range(3))
            if not found:
                break
            hi = cand
        with self.lock:
            self.max_id = max(self.max_id, hi)

    def probe_in_background(self):
        """Tastet die Obergrenze höchstens einmal am Tag ab, ohne den Wurf aufzuhalten."""
        with self.lock:
            if time.time() - self.probed < DAY:
                return
            self.probed = time.time()

        def run():
            try:
                self.probe_max()
            except Exception as exc:
                log.warning("%s: Obergrenze nicht geprüft: %s", self.key, exc)

        threading.Thread(target=run, name=f"probe-{self.key}", daemon=True).start()

    def random(self, free=False, safe=True):
        self.probe_in_background()
        for _ in range(self.attempts):
            model = self.exists(random.randint(1, self.max_id))
            if model and passes(model, free, safe):
                return model
        raise RuntimeError("Nach mehreren Versuchen kein passendes Modell gefunden")


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
    can_free = can_nsfw = True  # Thingiverse ist durchgehend kostenlos
    start_max, step = 7_000_000, 50_000
    API = "https://api.thingiverse.com"

    def __init__(self):
        super().__init__()
        self.token = secret("THINGIVERSE_TOKEN")
        if not self.token:
            self.enabled, self.reason = False, "Kein API-Token (THINGIVERSE_TOKEN) hinterlegt"

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


class Cults(Source):
    """Offizielle API. Würfelt ein zufälliges Wochenfenster seit 2014 und hält die Treffer vorrätig."""

    key, name, color = "cults", "Cults3D", "#822EF5"
    can_free = can_nsfw = True
    API = "https://cults3d.com/graphql"
    QUERY = """query($after: ISO8601DateTime, $before: ISO8601DateTime, $free: Boolean) {
      creationsBatch(limit: 50, offset: 0, onlyFree: $free, submittedAfter: $after, submittedBefore: $before) {
        results {
          name(locale: EN) url(locale: EN) illustrationImageUrl safe
          price(currency: EUR) { cents } creator { nick }
        } } }"""
    START = 1388534400  # 2014-01-01, Start von Cults
    WINDOW = 7 * DAY
    POOL_MAX = 500
    MIN_INTERVAL = 180  # Sekunden zwischen zwei API-Aufrufen, hält das Tageslimit (≈ 500) sicher ein

    def __init__(self):
        self.user, self.apikey = secret("CULTS_USER"), secret("CULTS_API_KEY")
        if not (self.user and self.apikey):
            self.enabled, self.reason = False, "Kein API-Schlüssel (CULTS_USER / CULTS_API_KEY) hinterlegt"
        self.lock = threading.Lock()
        self.pools = {False: [], True: []}  # Schlüssel: nur kostenlos?
        self.last_call = 0.0

    def fill(self, free):
        auth = base64.b64encode(f"{self.user}:{self.apikey}".encode()).decode()
        after = random.randint(self.START, int(time.time()) - self.WINDOW)
        iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731
        with self.lock:
            self.last_call = time.time()
        raw = http(
            self.API,
            {"query": self.QUERY, "variables": {"after": iso(after), "before": iso(after + self.WINDOW), "free": free}},
            headers={"Authorization": f"Basic {auth}"},
        )
        data = json.loads(raw)
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "Cults-API-Fehler"))
        items = ((data.get("data") or {}).get("creationsBatch") or {}).get("results") or []
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
            pool.extend(batch)
            del pool[: max(0, len(pool) - self.POOL_MAX)]
        return len(batch)

    def candidates(self, free, safe):
        with self.lock:
            return [m for m in self.pools[free] if passes(m, free, safe)]

    def random(self, free=False, safe=True):
        cands = self.candidates(free, safe)
        with self.lock:
            due = time.time() - self.last_call > self.MIN_INTERVAL
        # Auffüllen, wenn der Vorrat leer ist oder der Abstand zum letzten Aufruf es erlaubt.
        # Ein leeres Zeitfenster (frühe Jahre) wird bis zu dreimal neu gewürfelt.
        tries = 3 if not cands else (1 if due else 0)
        for _ in range(tries):
            try:
                self.fill(free)
            except Exception as exc:
                if cands:
                    log.warning("cults: Auffüllen fehlgeschlagen: %s", exc)
                    break
                raise
            cands = self.candidates(free, safe)
            if cands:
                break
        if not cands:
            raise RuntimeError("Kein passendes Modell im Vorrat")
        return dict(random.choice(cands))


SOURCES = OrderedDict((s.key, s) for s in (MakerWorld(), Printables(), Cults(), Thingiverse()))


# ------------------------------------------------------------- Ratenbegrenzung


class RateLimiter:
    """Einfaches Fenster pro Client: höchstens N Würfe je Minute."""

    def __init__(self, per_minute):
        self.per_minute = per_minute
        self.lock = threading.Lock()
        self.hits = {}

    def allow(self, client):
        now = time.time()
        with self.lock:
            if len(self.hits) > 10_000:  # Speicher begrenzen
                self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > now - 60}
            times = [t for t in self.hits.get(client, []) if t > now - 60]
            if len(times) >= self.per_minute:
                self.hits[client] = times
                return False
            times.append(now)
            self.hits[client] = times
            return True


LIMITER = RateLimiter(RATE_PER_MINUTE)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' https:; connect-src 'self'; manifest-src 'self'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


# --------------------------------------------------------------------- Server


class Handler(BaseHTTPRequestHandler):
    server_version = "PrintRoulette"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    def client(self):
        if TRUST_PROXY:
            fwd = self.headers.get("X-Forwarded-For", "")
            if fwd:
                return fwd.split(",")[0].strip()[:64]
        return self.client_address[0]

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
            if not src:
                self._json(404, {"error": "Unbekannte Quelle"})
                return
            if not src.enabled:
                self._json(503, {"error": src.reason})
                return
            if not LIMITER.allow(self.client()):
                self._json(429, {"error": "Zu viele Würfe, bitte kurz warten"}, extra={"Retry-After": "60"})
                return
            free = (params.get("free") or ["0"])[0] == "1"
            safe = (params.get("nsfw") or ["0"])[0] != "1"
            try:
                model = clean_model(src.random(free=free, safe=safe))
                model.update({"source": src.key, "sourceName": src.name, "color": src.color})
                self._json(200, model)
            except Exception as exc:
                log.warning("%s: %s", src.key, exc)
                self._json(502, {"error": f"{src.name} antwortet gerade nicht, bitte noch einmal versuchen"})
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
        ctype = mimetypes.guess_type(file)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "text/javascript"):
            ctype += "; charset=utf-8"
        with open(file, "rb") as fh:
            body = fh.read()
        if file.endswith(".html"):
            body = body.replace(b"__PUBLIC_URL__", PUBLIC_URL.encode())
        self._send(200, body, ctype, "public, max-age=300")


if __name__ == "__main__":
    if "--version" in sys.argv:
        print(__version__)
        raise SystemExit(0)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("image/svg+xml", ".svg")
    active = ", ".join(s.name for s in SOURCES.values() if s.enabled)
    log.info("Print Roulette läuft auf Port %s; aktive Quellen: %s", PORT, active)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

"""Print Roulette: zufällige 3D-Modelle von MakerWorld, Printables, Cults3D und Thingiverse."""
import base64
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8080"))
UA = os.environ.get("USER_AGENT", "PrintRoulette/1.0 (+https://roulette.hessis.eu)")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DAY = 24 * 3600


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
    req = urllib.request.Request(url, data=body, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def slug_title(slug):
    return re.sub(r"[-_]+", " ", slug).strip().title()


class Source:
    key = ""
    name = ""
    color = ""
    enabled = True
    reason = ""

    def info(self):
        return {"key": self.key, "name": self.name, "color": self.color,
                "enabled": self.enabled, "reason": self.reason}

    def random(self):
        raise NotImplementedError


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
        pages = [u for u in self.LOC_RE.findall(http(f"{self.BASE}/sitemaps/index.xml"))
                 if "/sitemaps/models.xml" in u]
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

    def random(self):
        pages = self.sitemap_pages()
        for _ in range(3):
            models = self.models_from_page(random.choice(pages))
            if models:
                mid, slug = random.choice(models)
                return {"id": str(mid), "title": slug_title(slug), "image": None, "creator": None,
                        "url": f"{self.BASE}/{self.LANG}/models/{mid}-{slug}"}
        raise RuntimeError("Keine Modelle in den geladenen Sitemap-Seiten")


# ------------------------------------------------- Zufalls-ID mit Obergrenze

class RandomIdSource(Source):
    """Würfelt IDs bis zu einer Obergrenze, die täglich nach oben getastet wird."""
    start_max = 1
    step = 1
    attempts = 10

    def __init__(self):
        self.lock = threading.Lock()
        self.max_id = int(os.environ.get(self.key.upper() + "_MAX_ID", self.start_max))
        self.probed = 0.0

    def exists(self, mid):
        """Gibt das Modell-Dict zurück oder None, wenn es die ID nicht gibt."""
        raise NotImplementedError

    def probe_max(self):
        with self.lock:
            if time.time() - self.probed < DAY:
                return
            self.probed = time.time()
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

    def random(self):
        try:
            self.probe_max()
        except Exception:
            pass
        for _ in range(self.attempts):
            model = self.exists(random.randint(1, self.max_id))
            if model:
                return model
        raise RuntimeError("Nach mehreren Versuchen kein gültiges Modell gefunden")


class Printables(RandomIdSource):
    key, name, color = "printables", "Printables", "#FA6831"
    start_max, step = 1_800_000, 20_000
    API = "https://api.printables.com/graphql/"
    QUERY = '{ print(id: "%d") { id name slug image { filePath } user { publicUsername } } }'

    def exists(self, mid):
        data = json.loads(http(self.API, {"query": self.QUERY % mid})).get("data", {}).get("print")
        if not data:
            return None
        img = data.get("image") or {}
        image = None
        if img.get("filePath"):
            image = "https://media.printables.com/" + img["filePath"]
        return {"id": data["id"], "title": data["name"], "image": image,
                "creator": (data.get("user") or {}).get("publicUsername"),
                "url": f"https://www.printables.com/model/{data['id']}-{data['slug']}"}


class Thingiverse(RandomIdSource):
    key, name, color = "thingiverse", "Thingiverse", "#248BFB"
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
        return {"id": str(data["id"]), "title": data["name"], "image": data.get("thumbnail"),
                "creator": (data.get("creator") or {}).get("name"), "url": data["public_url"]}


# -------------------------------------------------------------------- Cults3D

class Cults(Source):
    key, name, color = "cults", "Cults3D", "#822EF5"
    API = "https://cults3d.com/graphql"
    QUERY = """query($limit: Int!, $offset: Int!) {
      creations(limit: $limit, offset: $offset) {
        name(locale: EN) url(locale: EN) illustrationImageUrl creator { nick }
      } }"""
    BATCH = 50
    POOL_MAX = 500          # höchstens 10 Pakete im Speicher
    REFILL_EVERY = 180      # Sekunden zwischen zwei API-Aufrufen (weit unter 500/Tag)
    MAX_OFFSET = int(os.environ.get("CULTS_MAX_OFFSET", "50000"))

    def __init__(self):
        self.user, self.apikey = secret("CULTS_USER"), secret("CULTS_API_KEY")
        if not (self.user and self.apikey):
            self.enabled, self.reason = False, "Kein API-Schlüssel (CULTS_USER / CULTS_API_KEY) hinterlegt"
        self.lock = threading.Lock()
        self.pool, self.filled = [], 0.0

    def fill(self):
        auth = base64.b64encode(f"{self.user}:{self.apikey}".encode()).decode()
        offset = random.randint(0, self.MAX_OFFSET)
        raw = http(self.API, {"query": self.QUERY, "variables": {"limit": self.BATCH, "offset": offset}},
                   headers={"Authorization": f"Basic {auth}"})
        data = json.loads(raw)
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "Cults-API-Fehler"))
        items = data.get("data", {}).get("creations") or []
        batch = [{"id": c["url"].rstrip("/").rsplit("/", 1)[-1], "title": c["name"], "image": c.get("illustrationImageUrl"),
                  "creator": (c.get("creator") or {}).get("nick"), "url": c["url"]} for c in items if c.get("url")]
        if not batch:
            raise RuntimeError("Cults lieferte keine Modelle")
        with self.lock:
            self.pool = (self.pool + batch)[-self.POOL_MAX:]
            self.filled = time.time()

    def random(self):
        with self.lock:
            need = not self.pool or time.time() - self.filled > self.REFILL_EVERY
        if need:
            try:
                self.fill()
            except Exception:
                if not self.pool:
                    raise
        with self.lock:
            return dict(random.choice(self.pool))


SOURCES = OrderedDict((s.key, s) for s in (MakerWorld(), Printables(), Cults(), Thingiverse()))


# --------------------------------------------------------------------- Server

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype, cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/api/sources":
            self._json(200, [s.info() for s in SOURCES.values()])
            return
        if path == "/api/random":
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            src = SOURCES.get(params.get("source", "makerworld"))
            if not src:
                self._json(404, {"error": "Unbekannte Quelle"})
                return
            if not src.enabled:
                self._json(503, {"error": src.reason})
                return
            try:
                model = src.random()
                model.update({"source": src.key, "sourceName": src.name, "color": src.color})
                self._json(200, model)
            except Exception as exc:
                self._json(502, {"error": f"{src.name}: {exc}"})
            return
        if path == "/healthz":
            self._send(200, b"ok", "text/plain")
            return
        if path == "/":
            path = "/index.html"
        file = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not file.startswith(STATIC_DIR) or not os.path.isfile(file):
            self._send(404, b"not found", "text/plain")
            return
        ctype = "text/html; charset=utf-8" if file.endswith(".html") else "application/octet-stream"
        with open(file, "rb") as fh:
            self._send(200, fh.read(), ctype, "public, max-age=300")


if __name__ == "__main__":
    active = ", ".join(s.name for s in SOURCES.values() if s.enabled)
    print(f"Print Roulette läuft auf Port {PORT}; aktive Quellen: {active}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

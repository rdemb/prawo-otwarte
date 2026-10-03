import json
import mimetypes
import threading
import time
from collections import OrderedDict, deque
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

from . import __version__
from .cases import DOMAINS, BasalRouter, intake
from .settings import Settings
from .sources import EliClient, SourceError, normalize_act, validate_eli
from .store import Store

STATIC = Path(__file__).parent / "static"
SOURCES = json.loads((Path(__file__).parent / "config" / "sources.json").read_text())


class RateLimit:
    """Bounded per-process limiter. One worker is the documented pilot configuration."""
    def __init__(self):
        self.entries, self.global_hits, self.lock = OrderedDict(), deque(), threading.Lock()

    def allow(self, client):
        with self.lock:
            stamp = time.monotonic()
            while self.global_hits and self.global_hits[0] < stamp-60:
                self.global_hits.popleft()
            if len(self.global_hits) >= 120:
                return False
            hits = self.entries.setdefault(client, deque())
            self.entries.move_to_end(client)
            while hits and hits[0] < stamp-60:
                hits.popleft()
            if len(hits) >= 30:
                return False
            hits.append(stamp)
            self.global_hits.append(stamp)
            if len(self.entries) > 2048:
                self.entries.popitem(last=False)
            return True


class App:
    def __init__(self, settings=None, eli=None, router=None):
        self.settings = settings or Settings.from_env()
        self.store = Store(self.settings.data_dir)
        self.eli = eli or EliClient(self.settings.official_timeout)
        self.router = router or BasalRouter(self.settings)
        self.limiter = RateLimit()

    @staticmethod
    def read_json(env):
        if env.get("CONTENT_TYPE", "").split(";")[0].strip() != "application/json":
            raise ValueError("Wymagany format application/json.")
        try:
            size = int(env.get("CONTENT_LENGTH") or "0")
        except ValueError:
            raise ValueError("Nieprawidłowy rozmiar żądania.")
        if not 0 < size <= 16_384:
            raise ValueError("Żądanie jest puste lub zbyt duże.")
        data = json.loads(env["wsgi.input"].read(size))
        if not isinstance(data, dict):
            raise ValueError("Oczekiwano obiektu JSON.")
        return data

    @staticmethod
    def string(data, key, minimum=0, maximum=500):
        value = data.get(key, "")
        if not isinstance(value,str) or not minimum <= len(value.strip()) <= maximum:
            raise ValueError(f"Pole {key}: wymagana długość {minimum}–{maximum} znaków.")
        return value.strip()

    def __call__(self, env, start_response):
        headers = [("X-Content-Type-Options","nosniff"),("Referrer-Policy","no-referrer"),
                   ("X-Frame-Options","DENY"),("Cache-Control","no-store"),
                   ("Permissions-Policy","camera=(), microphone=(), geolocation=()"),
                   ("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")]
        if env.get("PATH_INFO", "").startswith("/api/"):
            headers.append(("Vary", "Origin"))
            origin = env.get("HTTP_ORIGIN")
            if origin and self.origin_allowed(env):
                headers.append(("Access-Control-Allow-Origin", origin))
                if env.get("REQUEST_METHOD") == "OPTIONS":
                    headers.extend([("Access-Control-Allow-Methods", "GET, POST"),
                                    ("Access-Control-Allow-Headers", "Content-Type"),
                                    ("Access-Control-Max-Age", "600")])
        try:
            status, data, mime = self.dispatch(env)
        except (ValueError, UnicodeError) as exc:
            status, data, mime = 400, {"error":str(exc) if not isinstance(exc,json.JSONDecodeError) else "Nieprawidłowy JSON."}, "application/json"
        except SourceError:
            status, data, mime = 503, {"error":"Oficjalne źródło jest chwilowo niedostępne. Spróbuj później lub przeszukaj lokalny katalog."}, "application/json"
        except Exception:
            # No stack/request body in public output; operators use tests and a private debugger.
            status, data, mime = 500, {"error":"Wewnętrzny błąd aplikacji. Spróbuj ponownie później."}, "application/json"
        if mime == "application/json":
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        headers.append(("Content-Type",mime+"; charset=utf-8"))
        if status != 204:
            headers.append(("Content-Length",str(len(data))))
        if status == 429:
            headers.append(("Retry-After","60"))
        reasons = {200:"OK",204:"No Content",400:"Bad Request",403:"Forbidden",404:"Not Found",405:"Method Not Allowed",429:"Too Many Requests",500:"Internal Server Error",503:"Service Unavailable"}
        start_response(f"{status} {reasons[status]}", headers)
        return [data]

    def origin_allowed(self, env):
        origin = env.get("HTTP_ORIGIN")
        own_origin = env.get("wsgi.url_scheme", "http") + "://" + env.get("HTTP_HOST", "")
        return origin == own_origin or origin in self.settings.allowed_origins

    def dispatch(self, env):
        path, method = env.get("PATH_INFO", "/"), env.get("REQUEST_METHOD","GET")
        if path.startswith("/api/"):
            if env.get("HTTP_ORIGIN") and not self.origin_allowed(env):
                return 403, {"error":"Niedozwolone pochodzenie żądania."}, "application/json"
            if method == "OPTIONS":
                methods = {"/api/status":"GET", "/api/search":"POST", "/api/act":"GET", "/api/intake":"POST"}
                requested_headers = {value.strip().lower() for value in env.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "").split(",") if value.strip()}
                if (not env.get("HTTP_ORIGIN") or path not in methods
                        or env.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD") != methods[path]
                        or requested_headers - {"content-type"}):
                    return 403, {"error":"Niedozwolone żądanie wstępne."}, "application/json"
                return 204, b"", "text/plain"
            if not self.limiter.allow(env.get("REMOTE_ADDR","local")):
                return 429, {"error":"Limit zapytań. Odczekaj minutę."}, "application/json"
            if path == "/api/status" and method == "GET":
                return 200, {"version":__version__, "stage":"research_preview", "corpus":self.store.status(),
                             "sources":SOURCES,"recent":self.store.recent(),"domains":{k:v["label"] for k,v in DOMAINS.items()},
                             "basal":{"enabled":self.settings.basal_enabled,"verified_live":False},
                             "eli_enabled":self.settings.allow_eli,"case_storage":False,"generative_answers":False}, "application/json"
            if path == "/api/search" and method == "POST":
                data = self.read_json(env)
                query = self.string(data,"query",2,160)
                mode = data.get("mode","local")
                if mode == "local":
                    items = self.store.search(query)
                    return 200, {"items":items,"mode":"local","returned":len(items),"temporal_verified":False}, "application/json"
                if mode != "eli":
                    raise ValueError("Nieobsługiwany tryb wyszukiwania.")
                if not self.settings.allow_eli:
                    raise SourceError("ELI disabled")
                publisher = self.string(data,"publisher",0,2)
                if publisher not in {"", "DU", "MP"}:
                    raise ValueError("Nieprawidłowy dziennik.")
                raw_year = data.get("year", "")
                year = None
                if raw_year != "":
                    if isinstance(raw_year,bool) or not isinstance(raw_year,(str,int)) or not str(raw_year).isdigit():
                        raise ValueError("Nieprawidłowy rok publikacji.")
                    year = int(raw_year)
                    if not 1900 <= year <= date.today().year:
                        raise ValueError("Nieprawidłowy rok publikacji.")
                offset = data.get("offset",0)
                if type(offset) is not int or not 0 <= offset <= 1_000_000:
                    raise ValueError("Nieprawidłowy numer strony.")
                result = self.eli.search(query,publisher=publisher or None,year=year,offset=offset,limit=20)
                items = [dict(normalize_act(item),fetched_at=result["fetched_at"]) for item in result["items"]]
                return 200, {"items":items,"mode":"eli","offset":offset,"total":result["total"],"returned":len(items),
                             "fetched_at":result["fetched_at"],"temporal_verified":False}, "application/json"
            if path == "/api/act" and method == "GET":
                eli = validate_eli(parse_qs(env.get("QUERY_STRING",""),max_num_fields=5).get("eli",[""])[0])
                record = self.store.get(eli)
                return (200,record,"application/json") if record else (404,{"error":"Akt nie jest zaimportowany lokalnie."},"application/json")
            if path == "/api/intake" and method == "POST":
                data = self.read_json(env)
                description = self.string(data,"description",20,4000)
                event_date = self.string(data,"event_date",0,10)
                if event_date:
                    if date.fromisoformat(event_date) > date.today():
                        raise ValueError("Podaj datę zdarzenia, które już nastąpiło, lub pozostaw pole puste.")
                domain = data.get("domain","unknown")
                if not isinstance(domain,str) or domain not in DOMAINS:
                    raise ValueError("Nieprawidłowa dziedzina.")
                return 200, intake(description,event_date,domain,self.router), "application/json"
            return 404, {"error":"Nie znaleziono zasobu."}, "application/json"
        if path == "/healthz" and method == "GET":
            return 200, {"status":"ok","version":__version__}, "application/json"
        if method != "GET":
            return 405, {"error":"Metoda niedozwolona."}, "application/json"
        allowed = {"/":"index.html", "/index.html":"index.html", "/app.js":"app.js", "/metrics.js":"metrics.js", "/style.css":"style.css", "/favicon.svg":"favicon.svg"}
        if path not in allowed:
            return 404, {"error":"Nie znaleziono strony."}, "application/json"
        target = STATIC / allowed[path]
        return 200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "text/plain"


def create_app():
    return App()

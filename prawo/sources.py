"""Official ELI adapter. Only administrator-chosen endpoints; no arbitrary URL fetch."""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

ELI_BASE = "https://api.sejm.gov.pl/eli"
ELI_ID = re.compile(r"(?:DU|MP)/\d{4}/\d{1,10}\Z")


class SourceError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_eli(value):
    if not isinstance(value, str) or not ELI_ID.fullmatch(value):
        raise ValueError("Nieprawidłowy identyfikator ELI.")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise SourceError("Źródło zmieniło adres. Wymagana weryfikacja adaptera.")


def fetch_bytes(url, *, timeout=12, body=None, max_bytes=8_000_000):
    headers = {"User-Agent": "PrawoOtwarte/0.1 (+https://github.com/rdemb/prawo-otwarte)",
               "Accept": "application/json, text/html;q=0.9"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with build_opener(NoRedirect).open(Request(url, data=body, headers=headers), timeout=timeout) as response:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise SourceError("Odpowiedź przekracza limit rozmiaru.")
            return data
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise SourceError("Źródło jest chwilowo niedostępne lub nie obsługuje tego zasobu.") from exc


def decode_json(data):
    try:
        return json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise SourceError("Źródło zwróciło nieprawidłowy JSON.") from exc


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.skip += 1
        elif tag in {"p", "div", "br", "h1", "h2", "h3", "li", "tr"} and not self.skip:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"} and self.skip:
            self.skip -= 1
        elif tag in {"p", "div", "h1", "h2", "h3", "li", "td"} and not self.skip:
            self.parts.append("\n" if tag != "td" else " ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(raw):
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8"))
    return "\n".join(line for line in (" ".join(x.split()) for x in "".join(parser.parts).splitlines()) if line)


def normalize_act(item):
    if not isinstance(item, dict):
        raise SourceError("Nieprawidłowa struktura aktu.")
    try:
        eli = validate_eli(item.get("ELI"))
    except ValueError as exc:
        raise SourceError("Brak poprawnego identyfikatora źródła.") from exc
    if not isinstance(item.get("title"), str) or not item["title"].strip():
        raise SourceError("Brak tytułu aktu.")
    return {
        "eli": eli, "title": item["title"], "publisher": eli.split("/")[0],
        "year": int(eli.split("/")[1]), "display_address": item.get("displayAddress", eli),
        "status": item.get("status", "brak statusu w źródle"),
        "source_url": f"https://eli.gov.pl/eli/{eli}/ogl",
        "published_on": item.get("promulgation"), "entry_into_force": item.get("entryIntoForce"),
        "source_changed_at": item.get("changeDate"), "has_html": bool(item.get("textHTML")),
        "temporal_verified": False,
    }


class EliClient:
    def __init__(self, timeout=12, fetcher=fetch_bytes):
        self.timeout, self.fetcher = timeout, fetcher

    def search(self, title="", *, publisher=None, year=None, offset=0, limit=20):
        params = {"title": title, "limit": max(1, min(limit, 100)), "offset": max(0, offset),
                  "sortBy": "promulgation", "sortDir": "desc"}
        if publisher:
            if publisher not in {"DU", "MP"}:
                raise ValueError("Nieobsługiwany dziennik.")
            params["publisher"] = publisher
        if year is not None:
            params["year"] = int(year)
        url = ELI_BASE + "/acts/search?" + urlencode(params)
        payload = decode_json(self.fetcher(url, timeout=self.timeout))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise SourceError("Nieprawidłowa lista wyników ELI.")
        total = payload.get("totalCount")
        if not isinstance(total, int) or total < 0:
            raise SourceError("Brak wiarygodnej liczby wyników ELI.")
        return {"items": payload["items"], "total": total, "url": url, "fetched_at": now()}

    def details(self, eli):
        url = ELI_BASE + "/acts/" + validate_eli(eli)
        raw = self.fetcher(url, timeout=self.timeout)
        payload = decode_json(raw)
        act = normalize_act(payload)
        if act["eli"] != eli:
            raise SourceError("Identyfikator odpowiedzi nie odpowiada żądanemu aktowi.")
        return payload, raw, url

    def text(self, eli):
        url = ELI_BASE + "/acts/" + validate_eli(eli) + "/text.html"
        raw = self.fetcher(url, timeout=self.timeout)
        try:
            text = html_to_text(raw)
        except UnicodeError as exc:
            raise SourceError("Nieobsługiwane kodowanie tekstu.") from exc
        if len(text) < 20:
            raise SourceError("Brak treści aktu w odpowiedzi źródła.")
        return text, raw, url

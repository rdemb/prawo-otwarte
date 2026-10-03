"""Build only the public static site; never publish a repository directory wholesale."""
import argparse
import json
import os
from pathlib import Path

from prawo.cases import DOMAINS
from prawo.settings import public_https_origin

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ("index.html", "style.css", "app.js", "favicon.svg", "pages.js")


def build(destination, api_base_url=""):
    api_base_url = public_https_origin(api_base_url) if api_base_url else ""
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Build destination must be empty; do not mix private files with the site.")
    destination.mkdir(parents=True, exist_ok=True)
    for name in PUBLIC_FILES:
        text = (ROOT / "prawo" / "static" / name).read_text()
        if name == "index.html":
            text = text.replace('<script src="./app.js" defer></script>', '<script src="./pages.js" defer></script>\n  <script src="./app.js" defer></script>')
        (destination / name).write_text(text)
    sources = json.loads((ROOT / "prawo" / "config" / "sources.json").read_text())
    for source in sources:
        if not api_base_url and source["id"] in {"eli-du", "eli-mp"}:
            source["scope"] = "Wyszukiwanie tytułów i odnośniki do oficjalnych publikacji. Lokalna kopia bazy nie jest jeszcze podłączona do tej strony."
    (destination / "pages-data.json").write_text(json.dumps({"domains":DOMAINS,"sources":sources,"api_base_url":api_base_url},ensure_ascii=False))
    (destination / ".nojekyll").touch()
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default="_site")
    parser.add_argument("--api-base-url", default=os.getenv("PRAWO_API_BASE_URL", ""))
    args = parser.parse_args()
    print(build(args.output, args.api_base_url))

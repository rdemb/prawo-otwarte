"""Build only the public static site; never publish a repository directory wholesale."""
import argparse
import json
from pathlib import Path

from prawo.cases import DOMAINS

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ("index.html", "style.css", "app.js", "favicon.svg", "pages.js")


def build(destination):
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
        if source["id"] in {"eli-du", "eli-mp"}:
            source["scope"] = "Wyszukiwanie tytułów i odnośniki do oficjalnych publikacji. Lokalna kopia bazy nie jest jeszcze podłączona do tej strony."
    (destination / "pages-data.json").write_text(json.dumps({"domains":DOMAINS,"sources":sources},ensure_ascii=False))
    (destination / ".nojekyll").touch()
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default="_site")
    print(build(parser.parse_args().output))

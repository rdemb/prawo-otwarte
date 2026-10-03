"""Build only the public static site; never publish a repository directory wholesale."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from prawo.cases import DOMAINS
from prawo.settings import public_https_origin

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = ("index.html", "style.css", "app.js", "metrics.js", "favicon.svg", "pages.js", "boot.js")
PUBLIC_BINARY_FILES = ("onest-latin.ttf",)


def asset_name(name, content):
    path = Path(name)
    digest = hashlib.sha256(content.encode() if isinstance(content, str) else content).hexdigest()[:16]
    return f"{path.stem}.{digest}{path.suffix}"


def build(destination, api_base_url=""):
    api_base_url = public_https_origin(api_base_url) if api_base_url else ""
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Build destination must be empty; do not mix private files with the site.")
    destination.mkdir(parents=True, exist_ok=True)
    files = {name:(ROOT / "prawo" / "static" / name).read_text() for name in PUBLIC_FILES}
    for name in PUBLIC_BINARY_FILES:
        content = (ROOT / "prawo" / "static" / name).read_bytes()
        versioned = asset_name(name, content)
        (destination / versioned).write_bytes(content)
        files["style.css"] = files["style.css"].replace(f"./{name}", f"./{versioned}")
    sources = json.loads((ROOT / "prawo" / "config" / "sources.json").read_text())
    for source in sources:
        if not api_base_url and source["id"] in {"eli-du", "eli-mp"}:
            source["scope"] = "Wyszukiwanie tytułów i odnośniki do oficjalnych publikacji. Lokalna kopia bazy nie jest jeszcze podłączona do tej strony."
    config = {"domains":DOMAINS,"sources":sources,"api_base_url":api_base_url}
    release = hashlib.sha256(json.dumps([files,config],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    config["build"] = release
    configuration = json.dumps(config,ensure_ascii=False)
    config_name = asset_name("pages-data.json", configuration)
    (destination / config_name).write_text(configuration)
    # Stable, read-only compatibility endpoint for operator checks; the UI uses the versioned file.
    (destination / "pages-data.json").write_text(configuration)
    files["pages.js"] = files["pages.js"].replace("'./pages-data.json'", repr('./' + config_name))
    html = files.pop("index.html").replace('<script src="./app.js" defer></script>', '<script src="./pages.js" defer></script>\n  <script src="./app.js" defer></script>')
    html = html.replace('</head>', f'  <meta name="prawo-build" content="{release}">\n</head>')
    for name, content in files.items():
        versioned = asset_name(name, content)
        (destination / versioned).write_text(content)
        html = html.replace(f'./{name}"', f'./{versioned}"')
    (destination / "index.html").write_text(html)
    (destination / ".nojekyll").touch()
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default="_site")
    parser.add_argument("--api-base-url", default=os.getenv("PRAWO_API_BASE_URL", ""))
    args = parser.parse_args()
    print(build(args.output, args.api_base_url))

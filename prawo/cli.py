import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .settings import Settings
from .sources import EliClient, SourceError, validate_eli
from .store import Store

SEEDS = ["DU/1997/483", "DU/1964/93", "DU/1974/141", "DU/2014/827"]
CORE_ACTS = json.loads((Path(__file__).parent / "config" / "core_acts.json").read_text())


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass  # no URLs or user-supplied content in development access logs


def import_act(store, client, eli, texts):
    item, raw, url = client.details(eli)
    store.upsert(item,raw=raw,source_url=url)
    text_imported = False
    if texts and item.get("textHTML"):
        text, body, source = client.text(eli)
        store.set_text(eli,text,body,source)
        text_imported = True
    return {"eli":eli,"metadata_imported":True,"text_imported":text_imported,
            "text_status":"imported" if text_imported else "html_unavailable" if texts else "not_requested", "temporal_verified":False}


def import_core_act(store, client, eli, texts):
    item,raw,url = client.details(eli)
    store.upsert(item,raw=raw,source_url=url)
    refs = item.get("references",{}).get("Inf. o tekście jednolitym",[])
    ids = [validate_eli(r["id"]) for r in refs]
    # Positions are ordered within a publisher/year, not by the API's list order.
    publication = max(ids,key=lambda x:tuple(map(int,x.split('/')[1:]))) if ids else eli
    if publication != eli:
        item,raw,url = client.details(publication)
        if eli not in [r.get("id") for r in item.get("references",{}).get("Tekst jednolity dla aktu",[])]:
            raise SourceError("Brak zwrotnego powiązania tekstu jednolitego.")
        store.upsert(item,raw=raw,source_url=url)
    # Selection is recorded before downloading. If the newest publication fails,
    # retrieval must not silently fall back to the previous/original wording.
    representation = "consolidated_publication" if publication != eli else "unified_editorial"
    store.select_answer_publication(eli,publication,representation,item.get("legalStatusDate"))
    imported = False
    if texts:
        kinds = ("T","O") if publication != eli else ("U",)
        files = item.get("texts",[])
        selected = next((f for kind in kinds for f in files if f.get("type") == kind),None)
        if not selected:
            raise SourceError("Brak odpowiedniej publikacji PDF; nie używamy pierwotnego HTML do odpowiedzi.")
        text,body,source = client.pdf_text(publication,selected["fileName"],selected["type"])
        store.set_text(publication,text,body,source,kind="pdf")
        imported = True
    return {"eli":eli,"publication":publication,"representation":representation,"text_imported":imported,"temporal_verified":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prawo Otwarte — explicit, bounded source ingestion")
    commands = parser.add_subparsers(dest="command",required=True)
    serve = commands.add_parser("serve",help="Local development server, never internet-facing")
    serve.add_argument("--port",type=int,default=8080)
    commands.add_parser("status")
    commands.add_parser("catalog-plan", help="Discover all official DU/MP years; metadata scope only")
    catalog = commands.add_parser("sync-catalog", help="Bounded, resumable first-pass metadata import across all DU/MP years")
    catalog.add_argument("--publisher", choices=["DU", "MP"])
    catalog.add_argument("--max-pages", type=int, default=10)
    catalog.add_argument("--pause", type=float, default=1.0)
    bootstrap = commands.add_parser("bootstrap",help="Import four identified acts as source examples, not all law")
    bootstrap.add_argument("--texts",action="store_true")
    core = commands.add_parser("import-core",help="Refresh 15 core acts and latest linked consolidated publications; PDF extraction requires pdftotext")
    core.add_argument("--texts",action="store_true")
    core.add_argument("--pause",type=float,default=1.0)
    one = commands.add_parser("import-act")
    one.add_argument("eli")
    one.add_argument("--text",action="store_true")
    sync = commands.add_parser("sync",help="Enumerate metadata for one publisher/year; resumable")
    sync.add_argument("--publisher",choices=["DU","MP"],required=True)
    sync.add_argument("--year",type=int,required=True)
    sync.add_argument("--max-pages",type=int,default=5)
    sync.add_argument("--pause",type=float,default=1.0)
    sync.add_argument("--resume",action="store_true")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    if args.command == "serve":
        from .web import App
        with make_server("127.0.0.1",args.port,App(settings),handler_class=QuietHandler) as server:
            print(f"Prawo Otwarte: http://127.0.0.1:{args.port} (development only)",flush=True)
            server.serve_forever()
        return
    store = Store(settings.data_dir)
    if args.command == "status":
        print(json.dumps(store.status(),ensure_ascii=False,indent=2))
        return
    if not settings.allow_eli:
        parser.error("Official source access is disabled by PRAWO_ALLOW_ELI.")
    client = EliClient(settings.official_timeout)
    try:
        if args.command == "catalog-plan":
            print(json.dumps(client.publishers(),ensure_ascii=False,indent=2))
        elif args.command == "sync-catalog":
            from .catalog import sync_catalog
            for result in sync_catalog(store,client,publisher=args.publisher,max_pages=args.max_pages,pause=args.pause):
                print(json.dumps(result,ensure_ascii=False),flush=True)
        elif args.command == "import-core":
            if not 0.25 <= args.pause <= 60:
                parser.error("pause: 0.25..60")
            failures = []
            for entry in CORE_ACTS:
                try:
                    result = import_core_act(store,client,entry["eli"],args.texts)
                except (SourceError,ValueError):
                    failures.append(entry["eli"])
                    result = {"eli":entry["eli"],"error":"Import failed; retry this act."}
                print(json.dumps(result,ensure_ascii=False),flush=True)
                time.sleep(args.pause)
            print(json.dumps({"requested":len(CORE_ACTS),"failed":failures,"corpus":store.status()},ensure_ascii=False),flush=True)
            if failures:
                sys.exit(1)
        elif args.command in {"bootstrap","import-act"}:
            ids = SEEDS if args.command == "bootstrap" else [args.eli]
            for eli in ids:
                print(json.dumps(import_act(store,client,eli,args.texts if args.command == "bootstrap" else args.text),ensure_ascii=False),flush=True)
                if len(ids) > 1:
                    time.sleep(0.5)
        elif args.command == "sync":
            if not 1900 <= args.year <= date.today().year or not 1 <= args.max_pages <= 1000 or not 0.25 <= args.pause <= 60:
                parser.error("year: 1900..current; max-pages: 1..1000; pause: 0.25..60")
            scope = f"{args.publisher}/{args.year}"
            offset = store.offset(scope) if args.resume else 0
            for _ in range(args.max_pages):
                result = client.search(publisher=args.publisher,year=args.year,offset=offset,limit=100)
                items = result["items"]
                if not items and offset < result["total"]:
                    raise SourceError("Źródło zwróciło pustą stronę przed końcem zakresu.")
                for item in items:
                    store.upsert(item,source_url=result["url"])
                offset += len(items)
                complete = offset >= result["total"]
                store.checkpoint(scope,offset,result["total"],complete)
                print(json.dumps({"scope":scope,"next_offset":offset,"reported_total":result["total"],"enumeration_finished":complete,"complete_polish_law":False}),flush=True)
                if complete:
                    break
                time.sleep(args.pause)
    except (SourceError,ValueError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

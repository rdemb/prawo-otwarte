import argparse
import json
import sys
import time
from datetime import date
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .settings import Settings
from .sources import EliClient, SourceError
from .store import Store

SEEDS = ["DU/1997/483", "DU/1964/93", "DU/1974/141", "DU/2014/827"]


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
    return {"eli":eli,"metadata_imported":True,"text_imported":text_imported,"temporal_verified":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prawo Otwarte — explicit, bounded source ingestion")
    commands = parser.add_subparsers(dest="command",required=True)
    serve = commands.add_parser("serve",help="Local development server, never internet-facing")
    serve.add_argument("--port",type=int,default=8080)
    commands.add_parser("status")
    bootstrap = commands.add_parser("bootstrap",help="Import four identified acts as source examples, not all law")
    bootstrap.add_argument("--texts",action="store_true")
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
        if args.command in {"bootstrap","import-act"}:
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

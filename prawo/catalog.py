"""Bounded first-pass national metadata ingestion, separate from answer sources."""
import time

from .sources import SourceError, normalize_act


def sync_catalog(store, client, *, publisher=None, max_pages=10, pause=1, sleep=time.sleep):
    if publisher not in {None, "DU", "MP"} or not 1 <= max_pages <= 1000 or not .25 <= pause <= 60:
        raise ValueError("publisher: DU/MP; max-pages: 1..1000; pause: .25..60")
    catalog = client.publishers()
    checkpoints = {row["scope"]:row for row in store.status()["imports"]}
    used = 0
    for group in catalog["publishers"]:
        if publisher and group["publisher"] != publisher:
            continue
        for year in group["years"]:
            scope = f'{group["publisher"]}/{year}'
            previous = checkpoints.get(scope, {})
            if previous.get("completed"):
                continue  # A prior enumeration, not a promise of current coverage.
            offset = previous.get("next_offset", 0)
            while used < max_pages:
                result = client.search(publisher=group["publisher"], year=year, offset=offset, limit=100)
                items, total = result["items"], result["total"]
                identities = [normalize_act(item)["eli"] for item in items]
                if (len(set(identities)) != len(identities) or
                    any(not eli.startswith(scope + "/") for eli in identities) or
                    (not items and offset < total) or offset + len(items) > total):
                    raise SourceError("Niespójna strona katalogu. Punkt wznowienia nie został przesunięty.")
                for item in items:
                    store.upsert(item, source_url=result["url"])
                offset += len(items)
                reached_end = offset >= total
                # Offset alone is not evidence of complete enumeration: a moving
                # source can repeat items between pages. Keep incomplete on drift.
                with store.connect() as db:
                    distinct = db.execute("SELECT COUNT(*) FROM acts WHERE publisher=? AND year=?",
                                          (group["publisher"], year)).fetchone()[0]
                complete = reached_end and distinct == total
                resume_offset = 0 if reached_end and not complete else offset
                store.checkpoint(scope, resume_offset, total, complete)
                used += 1
                yield {"scope":scope, "next_offset":resume_offset, "page_end_offset":offset, "reported_total":total,
                       "local_distinct":distinct, "enumeration_finished":complete,
                       "reconciliation_required":reached_end and not complete,
                       "pages_this_run":used, "texts_imported":0, "complete_polish_law":False}
                if reached_end and not complete:
                    raise SourceError("Liczba unikalnych aktów różni się od ELI. Wymagana ponowna enumeracja rocznika od offsetu 0 i rekonsyliacja ID.")
                if used >= max_pages:
                    return
                sleep(pause)
                if reached_end:
                    break

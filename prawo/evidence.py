"""Bounded lexical retrieval. Source excerpts are not a reconstruction of current law."""
import hashlib
import re

STOP = set("czy jak jaka jakie jaki kiedy gdzie mogę może można mam mnie jest są się nie tak dla oraz albo przez tego które który która przepisy mówią jeśli przy moje mojej moja chcę proszę pytanie prawo prawne sprawa sprawie dotyczy dotyczące czym tym ten tej to co do na ze od po we za i w z o a u".split())


def stem(word):
    return word[:5] if len(word) >= 6 else word[:-1] if len(word) == 5 and word[-1] in "yęa" else word


def terms(question):
    words = re.findall(r"[^\W_]+", question.lower(), re.UNICODE)
    # Conservative prefix matching handles common Polish inflections, not semantic search.
    result = list(dict.fromkeys(stem(w) for w in words if len(w) >= 3 and w not in STOP))[:20]
    if any(w.startswith("internet") for w in words):
        result.append("odległ")
    return result


def relevance(text, tokens):
    coverage = sum(bool(re.search(r"\b"+re.escape(t),text.lower())) for t in tokens)
    # The opening sentence often states what a provision regulates. Reward ordered
    # phrases there, e.g. 'okres wypowiedzenia umowy o pracę', not just word counts.
    opening = [stem(w) for w in re.findall(r"[^\W_]+",text[:450].lower()) if len(w) >= 3 and w not in STOP]
    phrase = " ".join(opening)
    ordered = sum(" ".join(tokens[i:i+n]) in phrase for n in (2,3,4) for i in range(max(0,len(tokens)-n+1)))
    # Matching another distinct concept must outweigh repeated phrases. Otherwise
    # a form heading can displace the operative article even with a worse BM25.
    return coverage * 10 + min(ordered, 9)


def passages(text):
    # Keep article boundaries where the source exposes them. Oversized articles are
    # explicitly labelled fragments; overlapping windows retain local context.
    annex = re.search(r"(?m)^Załącznik do obwieszczenia",text)
    if annex:
        text = text[annex.start():]
    sections = re.split(r"(?m)(?=^Art\.\s*\d|^Załączniki? (?:nr|do ustawy))", text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading = re.match(r"Art\.\s*\d+[a-zA-Z]*(?:\s*\[[^\]]+\])?\.?", section)
        label = heading.group(0) if heading else "Fragment tekstu"
        for start in range(0, len(section), 1800):
            body = section[max(0,start-200):start+1800].strip()
            if len(body) >= 30:
                yield label + (" · fragment" if len(section) > 1800 else ""), body


def index_passages(db, eli, body):
    db.execute("DELETE FROM passages WHERE eli=?", (eli,))
    digest = hashlib.sha256(body.encode()).hexdigest()
    db.executemany("INSERT INTO passages (eli,ordinal,label,body,text_sha256) VALUES (?,?,?,?,?)",
                  ((eli,i,label,text,digest) for i,(label,text) in enumerate(passages(body))))


def retrieve(store, question, limit=5):
    tokens = terms(question)
    if not tokens:
        return []
    expression = " OR ".join('"'+token+'"*' for token in tokens)
    with store.connect() as db:
        rows = db.execute("""SELECT p.*, a.title, a.text_fetched_at, a.fetched_at, ap.representation, ap.legal_status_date
            FROM passages_fts f JOIN passages p ON p.id=f.rowid JOIN acts a ON a.eli=p.eli
            JOIN answer_publications ap ON ap.eli=a.eli
            WHERE passages_fts MATCH ? AND a.text_stale=0 AND a.body!='' AND a.text_kind='pdf'
            ORDER BY bm25(passages_fts) LIMIT 60""", (expression,)).fetchall()
    # Prefer coverage of different query terms to repeated occurrences of one term.
    rows = sorted(rows,key=lambda r:relevance(r["body"],tokens),reverse=True)
    result = []
    for row in rows:
        # Adjacent overlapping fragments of the same article add little evidence.
        if any(s["eli"] == row["eli"] and s["label"] == row["label"] for s in result):
            continue
        result.append({"id":"S"+str(len(result)+1), "eli":row["eli"], "title":row["title"],
            "label":row["label"], "text":row["body"], "text_sha256":row["text_sha256"],
            "text_fetched_at":row["text_fetched_at"], "metadata_fetched_at":row["fetched_at"],
            "representation":row["representation"], "legal_status_date":row["legal_status_date"],
            "source_url":"https://eli.gov.pl/eli/"+row["eli"]+"/ogl", "temporal_verified":False})
        if len(result) >= limit:
            break
    return result

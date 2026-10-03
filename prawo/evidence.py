"""Bounded lexical retrieval. Source excerpts are not a reconstruction of current law."""
import hashlib
import math
import re

STOP = set("czy jak jaka jakie jaki kiedy gdzie mogę może można mam mnie jest są się nie tak dla oraz albo przez tego które który która przepisy mówią jeśli przy moje mojej moja chcę proszę pytanie prawo prawne sprawa sprawie dotyczy dotyczące czym tym ten tej to co do na ze od po we za i w z o a u".split())


def stem(word):
    return word[:5] if len(word) >= 6 else word[:-1] if len(word) == 5 and word[-1] in "yęa" else word


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


FAMILIES = {
    "zwrot": ("zwrot", "zwroc", "zwrac", "zwróc"),
    "najem": ("najem", "najm"),
    "lokal": ("lokal", "mieszk"),
    "złoż": ("złoż", "złoży", "skład"),
    "odleg": ("odleg", "internet"),
}
QUERY_STOP = set("ustawa ustawy ustawę ustawie kodeks kodeksu kodeksie artykuł artykułu artykule art mówi mówią stanowi pokaż przewiduje przewidują następuje następują według być będzie trzeba zasady zasad jakie jakich obowiązują reguluje zakres spraw wysokość wysokości długi długo długość najlepszy najlepiej prawach prawa prawo źródła źródło źródłach".split())


def concept(word):
    return next((key for key, variants in FAMILIES.items() if word.startswith(variants)), stem(word))


def query_terms(text):
    return list(dict.fromkeys(concept(w) for w in re.findall(r"[^\W_]+", text.lower())
                             if len(w) >= 3 and w not in STOP | QUERY_STOP))[:20]


def law_name(title):
    # Use the root act's primary name, not the gazette notice or acts it amends.
    name = re.sub(r"^ustawa z dnia .*? r\.\s*[-–]?\s*", "", title.lower())
    return re.split(r",| i o zmianie | z dnia ", name)[0]


def article_reference(question):
    match = re.search(r"\b(?:art\.?|artykuł(?:u|em|owi)?|artykule)\s+(\d+[a-z]?(?:\[\d+\])?)(?![\w\[])", question.lower())
    return match.group(1) if match else None


def needs_contract_details(question):
    # A generic contract operation does not identify employment, tenancy,
    # consumer sales, etc. Ask for facts before generating an apparent entitlement.
    tokens = set(query_terms(question)) - {"okres", "termin"}
    return "umow" in tokens and len(tokens) <= 2


def opening_sentence(text):
    text = re.sub(r"^Art\.\s*\d+[a-z]*(?:\[\d+\])?\.\s*(?:§\s*\d+\.\s*|\d+\.\s*)?", "", text)
    return re.split(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ])",text,maxsplit=1)[0]


def retrieve(store, question, limit=5):
    tokens = query_terms(question)
    scope = bool(re.search(r"\b(?:zakres|co reguluje|co określa|czego dotyczy)\b", question.lower()))
    article = article_reference(question)
    if article:
        tokens = [t for t in tokens if t != article]
    with store.connect() as db:
        catalog = db.execute("""SELECT ap.eli, a.title FROM answer_publications ap
            JOIN acts a ON a.eli=ap.root_eli""").fetchall()
        named = []
        if re.search(r"\b(?:ustaw\w*|kodeks\w*|konstytuc\w*|ordynac\w*|rozporządz\w*)\b", question.lower()):
            for act in catalog:
                name_tokens = set(query_terms(law_name(act["title"])))
                if name_tokens and name_tokens <= set(tokens):
                    named.append((act["eli"], name_tokens))
        # A reference to a document type absent from this corpus is not evidence
        # for a similarly numbered article in a different kind of act.
        if not named and re.search(r"\brozporządzen\w*[^?!.]{0,80}\b\d+/\d{4}\b", question.lower()) and not any("rozporządzen" in a["title"].lower() for a in catalog):
            return []
        selected = named[0] if len(named) == 1 else None
        if selected:
            tokens = [t for t in tokens if t not in selected[1]]
        if not tokens and not selected:
            return []
        filters = ["a.text_stale=0", "a.body!=''", "a.text_kind='pdf'"]
        params = []
        if selected:
            filters.append("p.eli=?"); params.append(selected[0])
        if article:
            filters.append("p.label IN (?,?)")
            params.extend(["Art. "+article+".", "Art. "+article+". · fragment"])
        def expression(items):
            return " OR ".join('"'+variant+'"*' for t in items for variant in FAMILIES.get(t,(t,)))
        lexical = bool(tokens) and not article
        if lexical:
            filters.append("passages_fts MATCH ?"); params.append(expression(tokens))
        rows = db.execute("""SELECT p.*, a.title, a.text_fetched_at, a.fetched_at, ap.representation, ap.legal_status_date
            FROM passages_fts f JOIN passages p ON p.id=f.rowid JOIN acts a ON a.eli=p.eli
            JOIN answer_publications ap ON ap.eli=a.eli WHERE """ + " AND ".join(filters) +
            (" ORDER BY bm25(passages_fts),p.id" if lexical else " ORDER BY p.ordinal,p.id") + " LIMIT 240", params).fetchall()
        count = db.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
        weights = {t:min(6.0,1+math.log((count+1)/(1+db.execute(
            "SELECT COUNT(*) FROM passages_fts WHERE passages_fts MATCH ?", (expression([t]),)).fetchone()[0]))) for t in tokens}
    # In 'Jak złożyć oświadczenie o ...', the requested action precedes its
    # background topic. Prefer the unit stating that action, not only its effects.
    focus = set(query_terms(re.split(r"\bo\b",question.lower(),maxsplit=1)[0])) & set(tokens) if question.lower().startswith("jak ") else set()
    if focus == set(tokens):
        focus = set()
    for t in focus:
        weights[t] *= 2
    def coverage(text):
        present = {t for t in tokens if any(re.search(r"\b"+re.escape(v),text.lower()) for v in FAMILIES.get(t,(t,)))}
        return sum(weights[t] for t in present) / (sum(weights.values()) or 1)
    ranked = []
    for row in rows:
        covered = coverage(row["body"])
        if tokens and not article and covered < .6:
            continue
        describes_scope = bool(re.search(r"\bustawa (?:określa|reguluje)\b",row["body"][:250].lower()))
        # A scope provision is appropriate for a scope question, but cannot
        # displace an operative rule merely by repeating the name of the act.
        score = covered * 100 + coverage(row["body"][:450]) * 5
        if focus:
            opening = opening_sentence(row["body"])
            score += 20 * sum(any(re.search(r"\b"+re.escape(v),opening.lower()) for v in FAMILIES.get(t,(t,))) for t in focus) / len(focus)
        score += (100 if scope else -25) if describes_scope else 0
        # Prefer a complete unit over a similarly relevant cut window. Keep
        # date-conditioned provisions available, but do not let a historical
        # subset outrank a general rule solely because its opening repeats nouns.
        if " · fragment" in row["label"]:
            score -= 20
        fixed_date = re.search(r"\b(?:przed|do) (?:dniem|dnia) [^.]{0,60}\b\d{4}\b",row["body"][:450].lower())
        if fixed_date and not re.search(r"\b\d{4}\b|\bhistorycz|\bdawn", question.lower()):
            score -= 15
        ranked.append((score,row))
    rows = [row for score,row in sorted(ranked,key=lambda x:x[0],reverse=True)]
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

"""
acquire_taiwan.py
-----------------
Harvest REAL, datable Taiwan classical poetry from Wikisource and emit per-year
poem records. No fabricated text: every poem is fetched from a cited source page.

Primary source for the pilot: chronologically-arranged single-author collections whose
section headers carry an explicit Western year, e.g. 窺園留草 (許南英, 1855-1917), whose
body is divided 甲申(1884) ... 乙未(1895) ... 丁巳(1917). Each year-section becomes one
dated unit of analysis, which is exactly what the 1895 time-series needs.

The full continuous NMTL 全臺詩 corpus (xdcm.nmtl.gov.tw) is unreachable from this
environment; `ingest_nmtl_export()` accepts its TSV/JSON export so the same pipeline scales
to the whole population once a researcher supplies it.

Output: data/raw/poems.jsonl  (one JSON object per dated section)
  {collection, author, year, year_raw, n_chars, text, source_url}
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

import requests
from opencc import OpenCC

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

WS_API = "https://zh.wikisource.org/w/api.php"
HDR = {"User-Agent": "loyalist-allusion-research/1.0 (academic; contact via repo)"}
S2T = OpenCC("s2t")

# Chinese numerals -> digit (incl. zero variants and fullwidth)
_NUM = {"〇": "0", "○": "0", "零": "0", "０": "0", "Ｏ": "0", "ｏ": "0",
        "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
        "六": "6", "七": "7", "八": "8", "九": "9"}

# A poem-body section header carries a reign era + an explicit western year.
# The appendix biography uses bare 干支（一八五五） headers (no reign era) -> excluded.
GANZHI = "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
REIGN = "(?:光緒|光绪|宣統|宣统|同治|咸豐|咸丰|中華民國|中华民国|民國|民国)"
HEADER_RE = re.compile(
    rf"([{GANZHI}][{GANZHI}](?:[至、][{GANZHI}][{GANZHI}])?[^\n（(]{{0,8}})"
    rf"[（(][^）)]*?{REIGN}[^）)]*?([一二三四五六七八九][八九][〇○零０Ｏ一二三四五六七八九][〇○零０Ｏ一二三四五六七八九])"
    rf"[^）)]*[）)]"
)


def cn_year_to_int(s: str) -> int | None:
    digits = "".join(_NUM.get(ch, "") for ch in s)
    if len(digits) == 4 and digits.isdigit():
        return int(digits)
    return None


def fetch_wikitext(page: str) -> str:
    r = requests.get(
        WS_API,
        params={"action": "parse", "page": page, "prop": "wikitext", "format": "json"},
        timeout=40, headers=HDR,
    ).json()
    if "parse" not in r:
        raise RuntimeError(f"cannot fetch {page}: {json.dumps(r)[:200]}")
    return r["parse"]["wikitext"]["*"]


# ---- wiki / editorial cleanup -------------------------------------------------
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HEADER_BLOCK = re.compile(r"\{\{header.*?\}\}", re.S)
_TAGS = re.compile(r"</?[^>]+>")          # <br>, <onlyinclude> etc.
_WIKILINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_NOTE_PAREN = re.compile(r"（按[^）]*）")  # editorial 按-notes inside text


def clean_wikitext(wt: str) -> str:
    wt = _HEADER_BLOCK.sub("", wt)
    for _ in range(3):  # nested templates
        wt = _TEMPLATE.sub("", wt)
    wt = _WIKILINK.sub(r"\1", wt)
    wt = _TAGS.sub("\n", wt)
    wt = _NOTE_PAREN.sub("", wt)
    return wt


def split_year_sections(wt: str) -> list[dict]:
    """Return [{year, year_raw, header, text}] for poem-body sections only."""
    matches = list(HEADER_RE.finditer(wt))
    sections = []
    for i, m in enumerate(matches):
        year = cn_year_to_int(m.group(2))
        if year is None:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wt)
        body = wt[start:end]
        sections.append({
            "year": year,
            "year_raw": m.group(0).strip(),
            "ganzhi": m.group(1).strip(),
            "offset": start,
            "text": body,
        })
    if not sections:
        return sections
    # A chronologically-arranged collection's poem body begins at its earliest year.
    # Drop any front-matter/preface headers (often dated later) that precede it.
    min_year = min(s["year"] for s in sections)
    body_start_off = min(s["offset"] for s in sections if s["year"] == min_year)
    sections = [s for s in sections if s["offset"] >= body_start_off]
    return sections


def harvest_collection(page: str, author: str, simplified: bool = True,
                       year_min: int = 1600, year_max: int = 1950) -> list[dict]:
    wt = fetch_wikitext(page)
    cleaned = clean_wikitext(wt)
    recs = []
    for sec in split_year_sections(cleaned):
        if not (year_min <= sec["year"] <= year_max):
            continue
        text = sec["text"]
        if simplified:
            text = S2T.convert(text)
        # keep only CJK + minimal structure; collapse whitespace
        recs.append({
            "collection": page,
            "author": author,
            "year": sec["year"],
            "year_raw": sec["year_raw"],
            "ganzhi": sec["ganzhi"],
            "text": text,
            "source_url": f"https://zh.wikisource.org/wiki/{page}",
        })
    return recs


# Confirmed-reachable, chronologically-dated single-author collections.
# (author, wikisource page, is_simplified). Extend as more are verified.
COLLECTIONS = [
    ("許南英", "窺園留草", True),
]


def ingest_nmtl_export(path: str) -> list[dict]:
    """Ingest the NMTL 全臺詩 export (TSV or JSON-lines) when a researcher supplies it.
    Expected fields: author, year (or period), text. This lets the SAME pipeline run on
    the full population without code changes."""
    p = Path(path)
    recs = []
    if p.suffix.lower() in (".jsonl", ".json"):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            recs.append(o)
    else:  # tsv
        import csv
        with p.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                recs.append(dict(row))
    return recs


def main():
    all_recs = []
    for author, page, simp in COLLECTIONS:
        try:
            recs = harvest_collection(page, author, simplified=simp)
            print(f"[{page}] {len(recs)} dated sections, "
                  f"years {min(r['year'] for r in recs)}-{max(r['year'] for r in recs)}")
            all_recs.extend(recs)
            time.sleep(1)
        except Exception as e:
            print(f"[{page}] FAILED: {e!r}")
    out = RAW / "poems.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in all_recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(all_recs)} records -> {out}")


if __name__ == "__main__":
    main()

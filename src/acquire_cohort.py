"""
acquire_cohort.py
-----------------
Harvest a multi-poet cohort of individually-sourced Taiwan poems from Wikisource for the
EXTERNAL-VALIDATION test (H5): do historian-labelled loyalists show higher loyalist-allusion
density than accommodationist/modernist poets? Labels come from data/poet_metadata.csv and
NEVER enter the measure.

Works are pulled from the Author namespace (作者:poet) where available, else from
author-tagged search results ('Title (poet)'). We keep lyric-length pages (CJK length in
[20, 800]) so long prose works (臺灣通史, essays) are excluded. Text is converted to
Traditional via OpenCC. No text is authored by us.

Output: data/raw/cohort_poems.jsonl
"""
from __future__ import annotations
import csv
import json
import time
from pathlib import Path

import requests

from acquire_taiwan import WS_API, HDR, S2T, clean_wikitext
from allusion_detect import cjk_only

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
META = ROOT / "data" / "poet_metadata.csv"


def _get(params):
    for _ in range(2):
        try:
            return requests.get(WS_API, params={**params, "format": "json"},
                                timeout=20, headers=HDR).json()
        except Exception:
            time.sleep(1.5)
    return {}


def author_works(poet: str) -> list[str]:
    """Union of parse-expanded links (catches transcluded work-lists) + paginated query
    links + author-tagged search hits. Robust to flaky individual calls."""
    titles = []
    for _ in range(2):  # (a) parse links expand transclusions
        r = _get({"action": "parse", "page": f"作者:{poet}", "prop": "links"})
        if "parse" in r:
            titles += [l["*"] for l in r["parse"].get("links", []) if l.get("ns") == 0]
            break
    plcontinue = None       # (b) query links, paginated
    for _ in range(20):
        params = {"action": "query", "prop": "links", "titles": f"作者:{poet}",
                  "plnamespace": 0, "pllimit": "max"}
        if plcontinue:
            params["plcontinue"] = plcontinue
        r = _get(params)
        for _pid, pdata in r.get("query", {}).get("pages", {}).items():
            titles += [l["title"] for l in pdata.get("links", [])]
        cont = r.get("continue", {}).get("plcontinue")
        if not cont:
            break
        plcontinue = cont
    # supplement with author-tagged search hits
    r2 = _get({"action": "query", "list": "search", "srsearch": poet, "srlimit": 50})
    for x in r2.get("query", {}).get("search", []):
        t = x["title"]
        if f"（{poet}）" in t or f"({poet})" in t:
            titles.append(t)
    seen, out = set(), []
    for t in titles:
        if t not in seen and not t.startswith(("作者:", "Author:", "Category:", "分類:")):
            seen.add(t); out.append(t)
    return out


def fetch_poem(title: str) -> str | None:
    r = _get({"action": "parse", "page": title, "prop": "wikitext"})
    if "parse" not in r:
        return None
    return clean_wikitext(r["parse"]["wikitext"]["*"])


def load_meta():
    rows = {}
    with META.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["poet"]] = row
    return rows


def main():
    meta = load_meta()
    # poets we attempt for the cohort (those with wikisource presence)
    cohort_poets = ["丘逢甲", "連橫", "許南英", "賴和", "孫元衡"]
    out_recs = []
    for poet in cohort_poets:
        m = meta.get(poet, {})
        titles = author_works(poet)[:200]
        kept = 0
        for t in titles:
            txt = fetch_poem(t)
            if not txt:
                continue
            trad = S2T.convert(txt)
            n = len(cjk_only(trad))
            if not (20 <= n <= 800):      # lyric-length filter -> excludes prose works
                continue
            out_recs.append({
                "author": poet,
                "title": t,
                "cohort": m.get("cohort", ""),
                "historian_label": m.get("historian_label", "unknown"),
                "n_chars": n,
                "text": trad,
                "source_url": f"https://zh.wikisource.org/wiki/{t}",
            })
            kept += 1
            time.sleep(0.05)
        print(f"{poet:6s} label={m.get('historian_label','?'):14s} kept {kept} lyric poems "
              f"(of {len(titles)} works)")
        time.sleep(0.3)
    out = RAW / "cohort_poems.jsonl"
    # merge with any existing records (flaky API -> accumulate across runs), dedupe by (author,title)
    existing = {}
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                existing[(o["author"], o["title"])] = o
    for r in out_recs:
        existing[(r["author"], r["title"])] = r
    with out.open("w", encoding="utf-8") as f:
        for r in existing.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(existing)} cohort poems (merged) -> {out}")


if __name__ == "__main__":
    main()

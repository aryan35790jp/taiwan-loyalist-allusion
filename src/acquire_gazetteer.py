"""
acquire_gazetteer.py
--------------------
Build an INDEPENDENT early/mid-Qing Taiwan poetry corpus from official Qing gazetteers
(府志/縣志) and 臺海使槎錄 — sources compiled by Qing officials, NOT by 連橫 or any loyalist.
Poems are extracted with the verse detector (verse.extract_verses), isolating regulated
shi from the surrounding prose. This corpus lets us check whether the mid-Qing 'trough' in
loyalist allusion replicates on an independently-curated source (selection-bias mitigation).

Output: data/raw/gazetteer_poems.jsonl  {source, page, n_chars, text}
"""
from __future__ import annotations
import json
import time
from pathlib import Path

import requests
from opencc import OpenCC

from verse import extract_verses
from allusion_detect import cjk_only

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WS_API = "https://zh.wikisource.org/w/api.php"
HDR = {"User-Agent": "loyalist-allusion-research/1.0"}
S2T = OpenCC("s2t")

# Qing-official gazetteers (all compiled 1700-1760s; non-loyalist provenance)
GAZETTEERS = ["諸羅縣志", "鳳山縣志", "臺海使槎錄", "重修臺灣縣志", "臺灣縣志"]
import re
_CLEAN = re.compile(r"\{\{[^{}]*\}\}")


def _get(params):
    for _ in range(3):
        try:
            return requests.get(WS_API, params={**params, "format": "json"},
                                timeout=25, headers=HDR).json()
        except Exception:
            time.sleep(2)
    return {}


def subpages(gz):
    for _ in range(4):
        r = _get({"action": "query", "list": "prefixsearch",
                  "pssearch": gz + "/", "pslimit": 60})
        out = [x["title"] for x in r.get("query", {}).get("prefixsearch", [])]
        if out:
            return out
        time.sleep(1.5)
    return []


def fetch(page):
    r = _get({"action": "parse", "page": page, "prop": "wikitext"})
    if "parse" not in r:
        return ""
    return r["parse"]["wikitext"]["*"]


def main():
    recs = []
    for gz in GAZETTEERS:
        pages = subpages(gz)
        gz_poems = 0
        for pg in pages:
            wt = fetch(pg)
            if not wt:
                continue
            for _ in range(3):
                wt = _CLEAN.sub("", wt)
            wt = S2T.convert(wt)
            verses = extract_verses(wt)
            for v in verses:
                n = len(cjk_only(v))
                if 16 <= n <= 400:
                    recs.append({"source": gz, "page": pg, "n_chars": n, "text": v})
                    gz_poems += 1
            time.sleep(0.2)
        print(f"{gz:14s} {len(pages):2d} pages -> {gz_poems} verses")
        time.sleep(0.4)
    out = RAW / "gazetteer_poems.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(recs)} gazetteer verses -> {out}")


if __name__ == "__main__":
    main()

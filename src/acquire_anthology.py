"""
acquire_anthology.py
---------------------
Extract a diachronic corpus from 連橫《臺灣詩乘》(6 vols, Wikisource). Poems are quoted in
『...』; 連橫 narrates chronologically and flags reign-eras / events in the surrounding prose.
We attribute each quoted poem to its NEAREST PRECEDING temporal marker and map that marker to
an approximate year. This is annotation-free (uses the anthology's own temporal cues).

Honest caveat recorded in output: 臺灣詩乘 is a curated anthology by a loyalist editor, so the
curve reflects 連橫's selection, not the whole population. The NMTL 全臺詩 run removes this
selection effect. We report the anthology curve as one of three convergent lines of evidence.

Output: data/raw/anthology_poems.jsonl
  {source, volume, marker, year_approx, n_chars, text, offset}
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

import requests
from opencc import OpenCC

from allusion_detect import cjk_only

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WS_API = "https://zh.wikisource.org/w/api.php"
HDR = {"User-Agent": "loyalist-allusion-research/1.0"}
S2T = OpenCC("s2t")

# temporal markers -> approximate mid-year. Order matters only for documentation.
MARKERS = [
    ("鄭氏", 1665), ("延平", 1665), ("國姓", 1665), ("東寧", 1675), ("永曆", 1660),
    ("寧靖", 1680), ("克塽", 1683),
    ("康熙", 1700), ("雍正", 1730), ("乾隆", 1760), ("嘉慶", 1805),
    ("道光", 1835), ("咸豐", 1855), ("同治", 1868), ("光緒", 1888),
    ("甲午", 1894), ("乙未", 1896), ("割臺", 1896), ("割台", 1896), ("馬關", 1895),
    ("內渡", 1896), ("臺灣民主國", 1895), ("明治", 1900), ("大正", 1918),
    ("丙午", 1906), ("民國", 1916),
]
MARKER_RE = re.compile("|".join(re.escape(m) for m, _ in MARKERS))
MARKER_YEAR = dict(MARKERS)


def fetch(page):
    for _ in range(3):
        try:
            r = requests.get(WS_API, params={"action": "parse", "page": page,
                             "prop": "wikitext", "format": "json"}, timeout=30, headers=HDR).json()
            if "parse" in r:
                return r["parse"]["wikitext"]["*"]
        except Exception:
            time.sleep(2)
    return ""


_CLEAN = re.compile(r"\{\{[^{}]*\}\}")


def extract_volume(vol: int) -> list[dict]:
    wt = fetch(f"臺灣詩乘/卷{vol}")
    if not wt:
        return []
    for _ in range(3):
        wt = _CLEAN.sub("", wt)
    wt = S2T.convert(wt)  # normalise to traditional
    # marker positions
    marks = [(m.start(), m.group()) for m in MARKER_RE.finditer(wt)]
    recs = []
    for pm in re.finditer(r"『([^』]+)』", wt):
        off = pm.start()
        text = pm.group(1)
        n = len(cjk_only(text))
        if n < 12:
            continue
        # nearest preceding marker
        prev = [(p, g) for p, g in marks if p <= off]
        if prev:
            _, g = prev[-1]
            year = MARKER_YEAR[g]; marker = g
        else:
            year = None; marker = None
        recs.append({"source": "臺灣詩乘", "volume": vol, "marker": marker,
                     "year_approx": year, "n_chars": n, "text": text, "offset": off})
    return recs


def main():
    allr = []
    for v in range(1, 7):
        recs = extract_volume(v)
        dated = [r for r in recs if r["year_approx"]]
        print(f"卷{v}: {len(recs)} poems, {len(dated)} dated by marker")
        allr.extend(recs)
        time.sleep(0.5)
    out = RAW / "anthology_poems.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in allr:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    dated = [r for r in allr if r["year_approx"]]
    print(f"wrote {len(allr)} poems ({len(dated)} dated) -> {out}")
    if dated:
        ys = [r["year_approx"] for r in dated]
        print("year span:", min(ys), "-", max(ys))


if __name__ == "__main__":
    main()

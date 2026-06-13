"""
acquire_pre1895.py
------------------
Harvest pre-1895 Qing-era Taiwan poets' INDIVIDUAL poems from Wikisource, processed
IDENTICALLY to the rupture cohort (acquire_cohort): author-namespace works, lyric-length
(20-800 CJK) individual poems, Traditional via OpenCC. This yields a register-matched,
independent-of-連橫 PRE-1895 baseline to compare against the rupture cohort.

Output: data/raw/pre1895_poems.jsonl  {author, title, cohort, historian_label, n_chars, text}
"""
from __future__ import annotations
import json
import time
from pathlib import Path

from acquire_cohort import author_works, fetch_poem, S2T
from allusion_detect import cjk_only

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# pre-1895 Taiwan poets reachable on Wikisource (personal/individual poems)
POETS = ["鄭用錫", "郁永河", "六十七", "張湄", "錢琦", "孫元衡"]


def main():
    recs = []
    for poet in POETS:
        titles = author_works(poet)[:80]
        kept = 0
        for t in titles:
            txt = fetch_poem(t)
            if not txt:
                continue
            trad = S2T.convert(txt)
            n = len(cjk_only(trad))
            if not (20 <= n <= 800):     # same lyric-length filter as rupture cohort
                continue
            recs.append({"author": poet, "title": t, "cohort": "pre1895",
                         "historian_label": "neutral", "n_chars": n, "text": trad,
                         "source_url": f"https://zh.wikisource.org/wiki/{t}"})
            kept += 1
            time.sleep(0.05)
        print(f"{poet:6s} kept {kept} lyric poems (of {len(titles)} works)")
        time.sleep(0.3)
    out = RAW / "pre1895_poems.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(recs)} pre-1895 poems -> {out}")


if __name__ == "__main__":
    main()

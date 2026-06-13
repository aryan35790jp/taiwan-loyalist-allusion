"""
acquire_ctext.py
----------------
Harvest register-matched personal poetry COLLECTIONS from ctext.org for the independent
rupture test (no 連橫 anthology, no defunct NMTL DB):

  RUPTURE-era loyalists (complete personal collections):
    嶺雲海日樓詩鈔 (丘逢甲), 劍花室詩集 (連橫)   [+ 許南英 窺園留草 already harvested]
  PRE-1895 baseline (personal collections by Qing-era Taiwan poets):
    赤嵌集 (孫元衡), 北郭園 (鄭用錫), etc. — discovered dynamically.

This gives a register-matched (personal-collection vs personal-collection) cross-cohort test,
which the gazetteer comparison could not (gazetteer = official descriptive verse).

Output: data/raw/ctext_poems.jsonl  {source, cohort, label, urn, n_chars, text}
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

import requests
from opencc import OpenCC

from verse import extract_verses
from allusion_detect import cjk_only

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
API = "https://api.ctext.org"
HDR = {"User-Agent": "loyalist-allusion-research/1.0"}
S2T = OpenCC("s2t")

# (title, cohort, historian_label)
TARGETS = [
    ("嶺雲海日樓詩鈔", "rupture", "loyalist"),     # 丘逢甲
    ("劍花室詩集", "rupture", "loyalist"),         # 連橫
    ("赤嵌集", "pre1895", "neutral"),              # 孫元衡 (~1705)
    ("北郭園詩鈔", "pre1895", "neutral"),          # 鄭用錫 (~1830)
    ("海音詩", "pre1895", "neutral"),              # 劉家謀 (~1850)
]


def _get(path, **params):
    for _ in range(3):
        try:
            return requests.get(f"{API}/{path}", params=params, timeout=25, headers=HDR).json()
        except Exception:
            time.sleep(2)
    return {}


def find_urn(title):
    r = _get("searchtexts", title=title)
    for b in r.get("books", []):
        if title in b.get("title", ""):
            return b.get("urn")
    bs = r.get("books", [])
    return bs[0].get("urn") if bs else None


def gettext_recursive(urn, depth=0, budget=None):
    """Walk a ctext work, collecting all passage text."""
    out = []
    r = _get("gettext", urn=urn)
    for key in ("fulltext", "text"):
        if key in r and isinstance(r[key], list):
            out.extend(r[key])
    subs = r.get("subsections", []) or r.get("chapters", [])
    if isinstance(subs, list):
        for s in subs[:200]:
            su = s if isinstance(s, str) else s.get("urn")
            if su and su != urn:
                time.sleep(0.25)
                out.extend(gettext_recursive(su, depth + 1))
    return out


def main():
    recs = []
    for title, cohort, label in TARGETS:
        urn = find_urn(title)
        if not urn:
            print(f"{title:14s} NOT FOUND on ctext")
            continue
        passages = gettext_recursive(urn)
        blob = S2T.convert("\n".join(p for p in passages if isinstance(p, str)))
        verses = extract_verses(blob)
        kept = 0
        for v in verses:
            n = len(cjk_only(v))
            if 16 <= n <= 400:
                recs.append({"source": title, "cohort": cohort, "label": label,
                             "urn": urn, "n_chars": n, "text": v})
                kept += 1
        print(f"{title:14s} urn={urn} passages={len(passages)} verses_kept={kept}")
        time.sleep(0.5)
    out = RAW / "ctext_poems.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(recs)} ctext verses -> {out}")


if __name__ == "__main__":
    main()

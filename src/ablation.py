"""
ablation.py
-----------
Robustness of the two loyalist peaks (Ming-Zheng founding era and the 1895 rupture) to
removing each lexicon category. A reviewer will ask: is the 1665 peak just 延平/國姓/東寧
(ming_zheng_taiwan) and the 1896 peak just 割臺/乙未 (direct_diction)? We recompute density
with each category ablated. If a peak survives ablation of its "obvious" driver, the loyalist
register there is broad, not a single-token artefact.
"""
from __future__ import annotations
import json
from pathlib import Path

from allusion_detect import load_default_lexicons, score_poem

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "anthology_poems.jsonl"
MIN_SPEC = 0.8

ABLATIONS = {
    "full": (),
    "minus ming_zheng_taiwan": ("ming_zheng_taiwan",),
    "minus direct_diction": ("direct_diction",),
    "minus both": ("ming_zheng_taiwan", "direct_diction"),
}
ERAS = {"Ming-Zheng (<=1683)": lambda y: y <= 1683,
        "mid-Qing (1700-1860)": lambda y: 1700 <= y <= 1860,
        "rupture (>=1894)": lambda y: y >= 1894}


def main():
    loy, ctl = load_default_lexicons()
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines()
            if l.strip() and json.loads(l).get("year_approx")]
    print(f"{'ablation':26s} " + " ".join(f"{e:>20s}" for e in ERAS))
    for name, excl in ABLATIONS.items():
        cells = []
        for era, cond in ERAS.items():
            num = den = 0.0
            for r in rows:
                if not cond(r["year_approx"]):
                    continue
                sc = score_poem(r["text"], loy, ctl, MIN_SPEC, exclude_categories=excl)
                num += sc["loyalist_weighted"]; den += sc["n_chars"]
            cells.append(100 * num / den if den else 0.0)
        print(f"{name:26s} " + " ".join(f"{c:20.3f}" for c in cells))


if __name__ == "__main__":
    main()

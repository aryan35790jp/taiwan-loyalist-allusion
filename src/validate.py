"""
validate.py  -- External validation (H5)
----------------------------------------
Do historian-labelled LOYALIST poets show higher loyalist-allusion density than
MODERNIST/ACCOMMODATIONIST poets? Labels (data/poet_metadata.csv) never enter the measure.

Reads data/raw/cohort_poems.jsonl (multi-poet, author-tagged). Reports:
  - per-author loyalist density (the honest unit, given author clustering),
  - group means (loyalist vs modernist/accommodationist),
  - a poem-level permutation test (EXPLORATORY; states the clustering caveat),
  - confirmatory note: needs >=3 authors per label group (available in full NMTL corpus).
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from allusion_detect import load_default_lexicons, score_poem

ROOT = Path(__file__).resolve().parent.parent
COHORT = ROOT / "data" / "raw" / "cohort_poems.jsonl"
RES = ROOT / "results"
RNG = np.random.default_rng(42)
MIN_SPEC = 0.8


def main():
    if not COHORT.exists():
        print("no cohort file; run acquire_cohort.py")
        return
    loy, ctl = load_default_lexicons()
    rows = []
    for line in COHORT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        sc = score_poem(s["text"], loy, ctl, min_specificity=MIN_SPEC)
        if sc["n_chars"] < 20:
            continue
        rows.append({"author": s["author"], "label": s["historian_label"],
                     "n": sc["n_chars"], "loy": sc["loyalist_weighted"],
                     "dens": sc["loyalist_density100"]})
    # also fold in the within-poet collection sections (許南英, label from metadata=loyalist)
    poems = ROOT / "data" / "raw" / "poems.jsonl"
    if poems.exists():
        for line in poems.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            s = json.loads(line)
            sc = score_poem(s["text"], loy, ctl, min_specificity=MIN_SPEC)
            if sc["n_chars"] < 20:
                continue
            rows.append({"author": s["author"], "label": "loyalist",
                         "n": sc["n_chars"], "loy": sc["loyalist_weighted"],
                         "dens": sc["loyalist_density100"]})

    # per-author density (length-weighted)
    num = defaultdict(float); den = defaultdict(float); lab = {}
    for r in rows:
        num[r["author"]] += r["loy"]; den[r["author"]] += r["n"]; lab[r["author"]] = r["label"]
    print(f"{'author':8s} {'label':14s} {'n_poems':>7s} {'loyalist_density100':>18s}")
    npoems = defaultdict(int)
    for r in rows:
        npoems[r["author"]] += 1
    author_dens = {}
    for a in num:
        d = 100.0 * num[a] / den[a] if den[a] else 0.0
        author_dens[a] = d
        print(f"{a:8s} {lab[a]:14s} {npoems[a]:7d} {d:18.3f}")

    LOY = {"loyalist"}
    OTH = {"modernist", "accommodationist", "neutral"}
    loy_rows = [r for r in rows if r["label"] in LOY]
    oth_rows = [r for r in rows if r["label"] in OTH]
    if not (loy_rows and oth_rows):
        print("\nneed both a loyalist and a non-loyalist group present.")
        return

    def pooled(rs):
        nn = sum(r["loy"] for r in rs); dd = sum(r["n"] for r in rs)
        return 100.0 * nn / dd if dd else 0.0

    obs = pooled(loy_rows) - pooled(oth_rows)
    # poem-level label permutation (EXPLORATORY: ignores author clustering)
    allr = loy_rows + oth_rows
    nL = len(loy_rows)
    idx = np.arange(len(allr))
    cnt = 0; B = 10000
    for _ in range(B):
        RNG.shuffle(idx)
        L = [allr[i] for i in idx[:nL]]; O = [allr[i] for i in idx[nL:]]
        if (pooled(L) - pooled(O)) >= obs:
            cnt += 1
    p = (cnt + 1) / (B + 1)

    loy_authors = sorted({a for a in lab if lab[a] in LOY})
    oth_authors = sorted({a for a in lab if lab[a] in OTH})
    print(f"\nloyalist group authors={loy_authors} pooled_density={pooled(loy_rows):.3f}")
    print(f"other    group authors={oth_authors} pooled_density={pooled(oth_rows):.3f}")
    print(f"difference (loyalist - other) = {obs:.3f}")
    print(f"poem-level permutation p (one-sided) = {p:.4f}  [EXPLORATORY: poems within an "
          f"author are not independent; n_loyalist_authors={len(loy_authors)}]")
    print("Confirmatory H5 requires >=3 authors per label group; the per-author means above "
          "are the honest descriptive unit.")

    out = {"author_density": author_dens, "label_of": lab,
           "loyalist_pooled": pooled(loy_rows), "other_pooled": pooled(oth_rows),
           "difference": obs, "perm_p_exploratory": p,
           "loyalist_authors": loy_authors, "other_authors": oth_authors}
    (RES / "validation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                         encoding="utf-8")


if __name__ == "__main__":
    main()

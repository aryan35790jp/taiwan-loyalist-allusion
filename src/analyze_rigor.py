"""
analyze_rigor.py
----------------
Free rigor upgrades on the existing anthology corpus (no new data):
 (#2) per-category heterogeneity: which loyalist trope-families drive the rupture surge.
 (#3) detector robustness: the primary contrast under multiple detector settings.
 (#1) clustering: block bootstrap by source volume (non-independence of poems within a vol).

Primary contrast throughout: rupture (>=1894) vs stable mid-Qing (1700-1860).
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from allusion_detect import load_lexicon, load_default_lexicons, detect, score_poem, LEX_DIR

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "anthology_poems.jsonl"
RES = ROOT / "results"
RNG = np.random.default_rng(42)


def load_rows():
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            if o.get("year_approx"):
                rows.append(o)
    return rows


def boot_diff(a_vals, a_den, b_vals, b_den, B=10000, clusters_a=None, clusters_b=None):
    """Bootstrap pooled-density diff (b-a). If clusters given, resample clusters (block)."""
    def pooled(vals, den):
        s = sum(vals); d = sum(den); return 100.0 * s / d if d else 0.0
    def resample(vals, den, clusters):
        if clusters is None:
            idx = RNG.integers(0, len(vals), len(vals))
            return [vals[i] for i in idx], [den[i] for i in idx]
        cl = defaultdict(list)
        for i, c in enumerate(clusters):
            cl[c].append(i)
        keys = list(cl)
        chosen = [keys[i] for i in RNG.integers(0, len(keys), len(keys))]
        v, d = [], []
        for c in chosen:
            for i in cl[c]:
                v.append(vals[i]); d.append(den[i])
        return v, d
    diffs = []
    for _ in range(B):
        bv, bd = resample(b_vals, b_den, clusters_b)
        av, ad = resample(a_vals, a_den, clusters_a)
        diffs.append(pooled(bv, bd) - pooled(av, ad))
    diffs = np.array(diffs)
    pt = pooled(b_vals, b_den) - pooled(a_vals, a_den)
    return pt, float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)), \
        float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean()))


def main():
    rows = load_rows()
    loy = load_lexicon(LEX_DIR / "loyalist_allusions.json")
    _, ctl = load_default_lexicons()
    id2cat = {e.id: e.category for e in loy.entries}
    id2spec = {e.id: e.specificity for e in loy.entries}
    cats = sorted({e.category for e in loy.entries})

    mid = [r for r in rows if 1700 <= r["year_approx"] <= 1860]
    rup = [r for r in rows if r["year_approx"] >= 1894]

    # ---------- (#2) per-category heterogeneity ----------
    print("=== (#2) per-category loyalist density: mid-Qing vs rupture (high-spec>=0.8) ===")
    print(f"{'category':32s} {'mid':>8s} {'rupture':>8s} {'diff':>8s} {'95% CI':>18s} {'p':>8s}")
    for cat in cats:
        def catvals(group):
            v, d = [], []
            for r in group:
                h = detect(r["text"], loy, min_specificity=0.8)
                w = sum(id2spec[i] for i in h.entries_hit if id2cat[i] == cat)
                v.append(w); d.append(h.n_chars)
            return v, d
        mv, md = catvals(mid); rv, rd = catvals(rup)
        pt, lo, hi, p = boot_diff(mv, md, rv, rd, B=4000)
        midd = 100*sum(mv)/sum(md) if sum(md) else 0
        rupd = 100*sum(rv)/sum(rd) if sum(rd) else 0
        print(f"{cat:32s} {midd:8.3f} {rupd:8.3f} {pt:8.3f}  [{lo:6.3f},{hi:6.3f}] {p:8.4f}")

    # ---------- (#3) detector robustness on the primary contrast ----------
    print("\n=== (#3) detector robustness: rupture vs mid-Qing under settings ===")
    settings = [
        ("high-spec>=0.8 presence", dict(min_specificity=0.8), "weighted"),
        ("full-lexicon presence", dict(min_specificity=0.0), "weighted"),
        ("full-lexicon raw tokens", dict(min_specificity=0.0), "tokens"),
        ("minus ming_zheng_taiwan", dict(min_specificity=0.8, exclude_categories=("ming_zheng_taiwan",)), "weighted"),
        ("minus direct_diction", dict(min_specificity=0.8, exclude_categories=("direct_diction",)), "weighted"),
        ("minus both", dict(min_specificity=0.8, exclude_categories=("ming_zheng_taiwan", "direct_diction")), "weighted"),
    ]
    for name, kw, mode in settings:
        def vals(group):
            v, d = [], []
            for r in group:
                h = detect(r["text"], loy, **kw)
                v.append(h.raw_tokens if mode == "tokens" else h.weighted_presence)
                d.append(h.n_chars)
            return v, d
        mv, md = vals(mid); rv, rd = vals(rup)
        pt, lo, hi, p = boot_diff(mv, md, rv, rd, B=4000)
        ratio = (100*sum(rv)/sum(rd)) / (100*sum(mv)/sum(md)) if sum(mv) and sum(md) else float('nan')
        print(f"{name:28s} diff={pt:6.3f} ratio={ratio:4.2f}x [{lo:6.3f},{hi:6.3f}] p={p:.4f}")

    # ---------- (#1) volume-clustered (block) bootstrap on primary contrast ----------
    print("\n=== (#1) volume-clustered block bootstrap (high-spec) ===")
    def vals_v(group):
        v, d, c = [], [], []
        for r in group:
            h = detect(r["text"], loy, min_specificity=0.8)
            v.append(h.weighted_presence); d.append(h.n_chars); c.append(r.get("volume"))
        return v, d, c
    mv, md, mc = vals_v(mid); rv, rd, rc = vals_v(rup)
    pt, lo, hi, p = boot_diff(mv, md, rv, rd, B=4000, clusters_a=mc, clusters_b=rc)
    print(f"rupture vs mid-Qing (cluster=volume): diff={pt:.3f} 95%CI[{lo:.3f},{hi:.3f}] p={p:.4f}")


if __name__ == "__main__":
    main()

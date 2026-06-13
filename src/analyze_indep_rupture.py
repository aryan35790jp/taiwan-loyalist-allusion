"""
analyze_indep_rupture.py
------------------------
The fully-independent rupture test (no 連橫 anthology at all): do independent rupture-cohort
poets' OWN complete works (丘逢甲 author-namespace; 許南英 1895-1900) show loyalist density
above the independent Qing-official gazetteer baseline?
"""
import json
import numpy as np
from pathlib import Path
from allusion_detect import load_default_lexicons, score_poem

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
LOY, CTL = load_default_lexicons()
RNG = np.random.default_rng(42)


def load(path, filt=None):
    rows = []
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        s = json.loads(l)
        if filt and not filt(s):
            continue
        sc = score_poem(s["text"], LOY, CTL, 0.8)
        if sc["n_chars"] >= 16:
            rows.append({"loy": sc["loyalist_weighted"], "ctl": sc["control_tokens"], "n": sc["n_chars"]})
    return rows


def dens(r, f="loy"):
    nu = sum(x[f] for x in r); de = sum(x["n"] for x in r)
    return 100 * nu / de if de else 0


def boot(a, b, f="loy", B=10000):
    ai, bi = np.arange(len(a)), np.arange(len(b)); d = []
    for _ in range(B):
        sb = dens([b[i] for i in RNG.choice(bi, len(b), True)], f)
        sa = dens([a[i] for i in RNG.choice(ai, len(a), True)], f)
        d.append(sb - sa)
    d = np.array(d)
    return dens(b, f) - dens(a, f), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(2 * min((d <= 0).mean(), (d >= 0).mean()))


def main():
    gaz = load(RAW / "gazetteer_poems.jsonl")
    qfj = load(RAW / "cohort_poems.jsonl", lambda s: s["author"] == "丘逢甲")
    lian = load(RAW / "cohort_poems.jsonl", lambda s: s["author"] == "連橫")
    xny = load(RAW / "poems.jsonl", lambda s: s.get("year") and 1895 <= s["year"] <= 1900)
    pool = qfj + lian + xny

    print(f"gazetteer baseline (indep)   n={len(gaz):4d} loy={dens(gaz):.3f} ctl={dens(gaz,'ctl'):.3f}")
    print(f"丘逢甲 complete works (indep) n={len(qfj):4d} loy={dens(qfj):.3f} ctl={dens(qfj,'ctl'):.3f}")
    print(f"連橫 own works (indep)        n={len(lian):4d} loy={dens(lian):.3f}")
    print(f"許南英 1895-1900 (indep)      n={len(xny):4d} loy={dens(xny):.3f}")
    print(f"INDEP rupture pool           n={len(pool):4d} loy={dens(pool):.3f} ctl={dens(pool,'ctl'):.3f}")

    for name, grp in [("丘逢甲 vs gazetteer", qfj), ("indep-rupture-pool vs gazetteer", pool)]:
        pt, lo, hi, p = boot(gaz, grp)
        ptc, loc, hic, pc = boot(gaz, grp, "ctl")
        print(f"\n{name}:")
        print(f"   loyalist diff={pt:.3f} 95%CI[{lo:.3f},{hi:.3f}] p={p:.4f}  (n={len(grp)})")
        print(f"   control  diff={ptc:.3f} 95%CI[{loc:.3f},{hic:.3f}] p={pc:.4f}")
        print(f"   DiD = {pt-ptc:.3f}")


if __name__ == "__main__":
    main()

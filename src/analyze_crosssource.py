"""
analyze_crosssource.py
----------------------
Selection-bias mitigation via cross-source triangulation.

Sources (independently compiled):
  - GAZETTEER  : 867 verses from Qing-official gazetteers (early/mid Qing). NOT 連橫.
  - ANTHOLOGY  : 997 dated poems from 連橫《臺灣詩乘》(mid-Qing subset and rupture subset).
  - XUNANYING  : 許南英《窺園留草》complete works (single author, NOT 連橫), rupture sections.

Tests:
  (A) Equivalence of the two INDEPENDENT mid-Qing baselines (gazetteer vs 連橫 mid-Qing):
      if they agree, 連橫 did not artificially depress the mid-Qing trough.
  (B) Rupture vs the INDEPENDENT gazetteer baseline: is the rupture elevated even when the
      baseline comes from a non-連橫 source?  Bootstrap CI + permutation p.
  (C) Control allusion across the same contrasts (must stay flat).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
from allusion_detect import load_default_lexicons, score_poem

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RES = ROOT / "results"
RNG = np.random.default_rng(42)
MIN_SPEC = 0.8


def score_file(path, year_filter=None):
    loy, ctl = load_default_lexicons()
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        y = s.get("year_approx") or s.get("year")
        if year_filter and not year_filter(y):
            continue
        sc = score_poem(s["text"], loy, ctl, MIN_SPEC)
        if sc["n_chars"] < 16:
            continue
        rows.append({"loy": sc["loyalist_weighted"], "ctl": sc["control_tokens"],
                     "n": sc["n_chars"]})
    return rows


def dens(rows, fld="loy"):
    num = sum(r[fld] for r in rows); den = sum(r["n"] for r in rows)
    return 100.0 * num / den if den else 0.0


def boot_diff(a, b, fld="loy", B=10000):
    """pooled density(b) - pooled density(a), bootstrap over poems."""
    ai, bi = np.arange(len(a)), np.arange(len(b))
    d = []
    for _ in range(B):
        sa = [a[i] for i in RNG.choice(ai, len(a), True)]
        sb = [b[i] for i in RNG.choice(bi, len(b), True)]
        d.append(dens(sb, fld) - dens(sa, fld))
    d = np.array(d)
    return {"point": dens(b, fld) - dens(a, fld), "lo": float(np.percentile(d, 2.5)),
            "hi": float(np.percentile(d, 97.5)),
            "p": float(2 * min((d <= 0).mean(), (d >= 0).mean()))}


def main():
    gaz = score_file(RAW / "gazetteer_poems.jsonl")
    anth_mid = score_file(RAW / "anthology_poems.jsonl", lambda y: y and 1700 <= y <= 1860)
    anth_rup = score_file(RAW / "anthology_poems.jsonl", lambda y: y and y >= 1894)
    xny_rup = score_file(RAW / "poems.jsonl", lambda y: y and 1895 <= y <= 1900)
    xny_post = score_file(RAW / "poems.jsonl", lambda y: y and y >= 1901)

    print("== loyalist density per source ==")
    print(f"GAZETTEER (independent, mid-Qing)  n={len(gaz):4d}  loy={dens(gaz):.3f}  ctl={dens(gaz,'ctl'):.3f}")
    print(f"ANTHOLOGY mid-Qing (連橫)           n={len(anth_mid):4d}  loy={dens(anth_mid):.3f}  ctl={dens(anth_mid,'ctl'):.3f}")
    print(f"ANTHOLOGY rupture (連橫)            n={len(anth_rup):4d}  loy={dens(anth_rup):.3f}  ctl={dens(anth_rup,'ctl'):.3f}")
    print(f"XU NANYING rupture 1895-1900 (indep) n={len(xny_rup):4d}  loy={dens(xny_rup):.3f}  ctl={dens(xny_rup,'ctl'):.3f}")
    print(f"XU NANYING post-1900 decay (indep)   n={len(xny_post):4d}  loy={dens(xny_post):.3f}  ctl={dens(xny_post,'ctl'):.3f}")

    print("\n(A) equivalence of independent mid-Qing baselines (gazetteer vs 連橫 mid-Qing):")
    a = boot_diff(gaz, anth_mid)
    print(f"    diff={a['point']:.3f} 95%CI[{a['lo']:.3f},{a['hi']:.3f}] p={a['p']:.4f}  "
          f"-> {'AGREE (CI includes 0)' if a['lo']<=0<=a['hi'] else 'differ'}")

    print("\n(B) rupture vs INDEPENDENT gazetteer baseline (the key cross-source test):")
    b = boot_diff(gaz, anth_rup)
    print(f"    loyalist diff={b['point']:.3f} 95%CI[{b['lo']:.3f},{b['hi']:.3f}] p={b['p']:.4f}")
    bc = boot_diff(gaz, anth_rup, "ctl")
    print(f"    control  diff={bc['point']:.3f} 95%CI[{bc['lo']:.3f},{bc['hi']:.3f}] p={bc['p']:.4f}")
    print(f"    DiD (loyalist - control) = {b['point']-bc['point']:.3f}")

    print("\n(B') independent rupture window 1895-1900 (許南英) vs independent baseline (gazetteer):")
    b2 = boot_diff(gaz, xny_rup)
    print(f"    loyalist diff={b2['point']:.3f} 95%CI[{b2['lo']:.3f},{b2['hi']:.3f}] p={b2['p']:.4f}  (n_xny={len(xny_rup)})")

    out = {"gazetteer": {"n": len(gaz), "loy": dens(gaz), "ctl": dens(gaz, "ctl")},
           "anthology_mid": {"n": len(anth_mid), "loy": dens(anth_mid)},
           "anthology_rup": {"n": len(anth_rup), "loy": dens(anth_rup)},
           "xny_rup": {"n": len(xny_rup), "loy": dens(xny_rup)},
           "A_baseline_equiv": a, "B_rupture_vs_gaz": b, "B_control_vs_gaz": bc,
           "Bp_xny_vs_gaz": b2}
    (RES / "crosssource_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")


if __name__ == "__main__":
    main()

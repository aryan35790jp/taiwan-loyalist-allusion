"""
analyze_anthology.py
--------------------
Diachronic loyalist-allusion density across 臺灣詩乘 (997 marker-dated poems, 1665-1896).
Reports density per era-bucket, the rupture (>=1894) vs pre-rupture contrast with a
poem-resampling bootstrap, and the loyalist-vs-control specificity check. Saves a figure.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from allusion_detect import load_default_lexicons, score_poem

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "anthology_poems.jsonl"
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
RNG = np.random.default_rng(42)
MIN_SPEC = 0.8
RUPTURE_FROM = 1894


def load():
    loy, ctl = load_default_lexicons()
    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        s = json.loads(line)
        if not s.get("year_approx"):
            continue
        sc = score_poem(s["text"], loy, ctl, min_specificity=MIN_SPEC)
        rows.append({"year": s["year_approx"], "n": sc["n_chars"],
                     "loy": sc["loyalist_weighted"], "ctl": sc["control_tokens"]})
    return rows


def pooled(rs, fld):
    num = sum(r[fld] for r in rs); den = sum(r["n"] for r in rs)
    return 100.0 * num / den if den else 0.0


def boot(pre, rup, fld, B=10000):
    def p(s):
        n = sum(r[fld] for r in s); d = sum(r["n"] for r in s); return 100*n/d if d else 0
    diffs = []
    pi = np.arange(len(pre)); ri = np.arange(len(rup))
    for _ in range(B):
        bp = [pre[i] for i in RNG.choice(pi, len(pre), True)]
        br = [rup[i] for i in RNG.choice(ri, len(rup), True)]
        diffs.append(p(br) - p(bp))
    d = np.array(diffs)
    return {"point": p(rup)-p(pre), "lo": float(np.percentile(d,2.5)),
            "hi": float(np.percentile(d,97.5)), "p": float(2*min((d<=0).mean(),(d>=0).mean()))}


def main():
    rows = load()
    by = defaultdict(list)
    for r in rows:
        by[r["year"]].append(r)
    years = sorted(by)
    print(f"{'era~year':>9s} {'n':>4s} {'loyalist':>9s} {'control':>9s}")
    loy_curve, ctl_curve = [], []
    for y in years:
        L = pooled(by[y], "loy"); C = pooled(by[y], "ctl")
        loy_curve.append(L); ctl_curve.append(C)
        print(f"{y:9d} {len(by[y]):4d} {L:9.3f} {C:9.3f}")

    pre = [r for r in rows if r["year"] < RUPTURE_FROM]
    rup = [r for r in rows if r["year"] >= RUPTURE_FROM]
    mid = [r for r in rows if 1700 <= r["year"] <= 1860]   # stable mid-Qing trough
    mz = [r for r in rows if r["year"] <= 1683]             # Ming-Zheng founding
    bL = boot(pre, rup, "loy"); bC = boot(pre, rup, "ctl")
    print(f"\nLOYALIST rupture(>={RUPTURE_FROM}) vs ALL-pre: pre={pooled(pre,'loy'):.3f} "
          f"rup={pooled(rup,'loy'):.3f} diff={bL['point']:.3f} "
          f"95%CI[{bL['lo']:.3f},{bL['hi']:.3f}] p={bL['p']:.4f}  (n_pre={len(pre)},n_rup={len(rup)})")
    print(f"CONTROL  rupture vs ALL-pre: pre={pooled(pre,'ctl'):.3f} rup={pooled(rup,'ctl'):.3f} "
          f"diff={bC['point']:.3f} 95%CI[{bC['lo']:.3f},{bC['hi']:.3f}] p={bC['p']:.4f}")
    print(f"difference-in-differences (loyalist - control) = {bL['point']-bC['point']:.3f}")

    # theoretically-motivated contrast: rupture vs the STABLE mid-Qing trough
    bLm = boot(mid, rup, "loy"); bCm = boot(mid, rup, "ctl")
    print(f"\n*** PRIMARY (bimodal-motivated) contrast ***")
    print(f"LOYALIST rupture(>=1894) vs mid-Qing(1700-1860): mid={pooled(mid,'loy'):.3f} "
          f"rup={pooled(rup,'loy'):.3f} diff={bLm['point']:.3f} "
          f"95%CI[{bLm['lo']:.3f},{bLm['hi']:.3f}] p={bLm['p']:.4f}  (n_mid={len(mid)},n_rup={len(rup)})")
    print(f"CONTROL  rupture vs mid-Qing: mid={pooled(mid,'ctl'):.3f} rup={pooled(rup,'ctl'):.3f} "
          f"diff={bCm['point']:.3f} 95%CI[{bCm['lo']:.3f},{bCm['hi']:.3f}] p={bCm['p']:.4f}")
    print(f"DiD (loyalist - control) = {bLm['point']-bCm['point']:.3f}")
    print(f"\nMing-Zheng(<=1683) loyalist={pooled(mz,'loy'):.3f} vs mid-Qing={pooled(mid,'loy'):.3f} "
          f"-> bimodal ratio rupture/mid={pooled(rup,'loy')/pooled(mid,'loy'):.2f}x, "
          f"MingZheng/mid={pooled(mz,'loy')/pooled(mid,'loy'):.2f}x")

    # figure
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(years, loy_curve, "-o", color="#b22222", label="loyalist (spec>=0.8)")
    ax.plot(years, ctl_curve, "-s", color="#4444aa", alpha=.6, label="neutral control")
    ax.axvline(1894, color="k", ls="--", lw=1, label="1894-95 rupture")
    ax.set_xlabel("approx. era year (連橫 marker)"); ax.set_ylabel("density per 100 chars")
    ax.set_title("Loyalist vs control allusion across Taiwan Shi Cheng (1665-1896), n=997")
    ax.legend(); fig.tight_layout(); fig.savefig(RES / "figure_anthology.png", dpi=150)

    out = {"years": years, "loyalist_curve": loy_curve, "control_curve": ctl_curve,
           "n_per_year": {int(y): len(by[y]) for y in years},
           "rupture_vs_allpre_loyalist": bL, "rupture_vs_allpre_control": bC,
           "rupture_vs_midqing_loyalist": bLm, "rupture_vs_midqing_control": bCm,
           "rupture_from": RUPTURE_FROM}
    (RES / "anthology_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                encoding="utf-8")


if __name__ == "__main__":
    main()

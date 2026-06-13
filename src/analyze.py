"""
analyze.py
----------
Compute the loyalist-allusion trajectory across 1895 from dated poem sections.

Primary measures per dated section:
  loyalist_density100  = 100 * (sum specificity over distinct high-spec loyalist entries) / CJK_chars
  control_density100   = 100 * (control tokens) / CJK_chars

Primary contrast (the paper's headline):
  loyalist density in the rupture window (1895-1900) vs the pre-rupture baseline (<1895),
  AND the same contrast for the neutral control. The loyalist rise must EXCEED the control
  rise, otherwise it is just a general increase in allusiveness.

Also: a ruptures changepoint on the loyalist series, and a bootstrap CI on the
rupture-minus-baseline difference (sections resampled within period).

Run: python src/analyze.py
Outputs: results/yearly.csv, results/summary.json, results/figure_curve.png
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

from allusion_detect import load_default_lexicons, score_poem

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "poems.jsonl"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

RNG = np.random.default_rng(42)
MIN_SPEC = 0.8          # primary analysis uses high-specificity loyalist entries
RUPTURE = (1895, 1900)  # rupture window
PRE_MAX = 1894          # pre-rupture baseline


def load_sections():
    return [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]


def score_sections(sections, min_spec=MIN_SPEC):
    loy, ctl = load_default_lexicons()
    rows = []
    for s in sections:
        sc = score_poem(s["text"], loy, ctl, min_specificity=min_spec)
        if sc["n_chars"] < 80:      # skip near-empty sections
            continue
        rows.append({
            "author": s["author"], "year": s["year"], "n_chars": sc["n_chars"],
            "loyalist_weighted": sc["loyalist_weighted"], "loyalist_density100": sc["loyalist_density100"],
            "control_tokens": sc["control_tokens"], "control_density100": sc["control_density100"],
            "loyalist_entries": ";".join(sc["loyalist_entries"]),
        })
    return rows


def pooled_density(rows, lo, hi, field_num, field_den="n_chars"):
    num = sum(r[field_num] for r in rows if lo <= r["year"] <= hi)
    den = sum(r[field_den] for r in rows if lo <= r["year"] <= hi)
    return 100.0 * num / den if den else 0.0


def bootstrap_diff(rows, num_field, n_boot=10000):
    """Bootstrap (pooled rupture density - pooled pre density), resampling sections."""
    pre = [r for r in rows if r["year"] <= PRE_MAX]
    rup = [r for r in rows if RUPTURE[0] <= r["year"] <= RUPTURE[1]]
    if not pre or not rup:
        return None
    def pooled(sample):
        num = sum(r[num_field] for r in sample)
        den = sum(r["n_chars"] for r in sample)
        return 100.0 * num / den if den else 0.0
    diffs = []
    pre_i = np.arange(len(pre)); rup_i = np.arange(len(rup))
    for _ in range(n_boot):
        bp = [pre[i] for i in RNG.choice(pre_i, len(pre), replace=True)]
        br = [rup[i] for i in RNG.choice(rup_i, len(rup), replace=True)]
        diffs.append(pooled(br) - pooled(bp))
    diffs = np.array(diffs)
    return {
        "point": pooled(rup) - pooled(pre),
        "ci_lo": float(np.percentile(diffs, 2.5)),
        "ci_hi": float(np.percentile(diffs, 97.5)),
        "p_two_sided": float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())),
    }


def changepoint(rows):
    try:
        import ruptures as rpt
    except Exception:
        return None
    rows_sorted = sorted(rows, key=lambda r: r["year"])
    sig = np.array([r["loyalist_density100"] for r in rows_sorted])
    years = [r["year"] for r in rows_sorted]
    if len(sig) < 5:
        return None
    algo = rpt.Dynp(model="l2", min_size=2, jump=1).fit(sig)
    bkps = algo.predict(n_bkps=1)
    cp_idx = bkps[0] - 1
    return {"changepoint_year": years[min(cp_idx, len(years) - 1)],
            "years": years, "signal": sig.tolist()}


def make_figure(rows, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = sorted(rows, key=lambda r: r["year"])
    yr = [r["year"] for r in rows]
    loy = [r["loyalist_density100"] for r in rows]
    ctl = [r["control_density100"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(yr, loy, "-o", color="#b22222", label="loyalist allusion (spec>=0.8)")
    ax.plot(yr, ctl, "-s", color="#4444aa", alpha=.7, label="neutral control allusion")
    ax.axvline(1895, color="k", ls="--", lw=1, label="1895 cession")
    ax.set_xlabel("year"); ax.set_ylabel("density per 100 chars")
    ax.set_title("Loyalist vs control allusion density across 1895 "
                 f"(pilot: Xu Nanying, n={len(rows)} dated sections)")
    ax.legend()
    fig.tight_layout(); fig.savefig(RES / "figure_curve.png", dpi=150)


def main():
    sections = load_sections()
    rows = score_sections(sections, MIN_SPEC)
    rows_full = score_sections(sections, 0.0)  # sensitivity: all loyalist entries

    summary = {
        "n_sections": len(rows),
        "authors": sorted({r["author"] for r in rows}),
        "year_range": [min(r["year"] for r in rows), max(r["year"] for r in rows)],
        "min_specificity_primary": MIN_SPEC,
        "loyalist": {
            "pre_density": pooled_density(rows, 1600, PRE_MAX, "loyalist_weighted"),
            "rupture_density": pooled_density(rows, *RUPTURE, "loyalist_weighted"),
            "post1900_density": pooled_density(rows, 1901, 1950, "loyalist_weighted"),
            "bootstrap_rupture_vs_pre": bootstrap_diff(rows, "loyalist_weighted"),
        },
        "control": {
            "pre_density": pooled_density(rows, 1600, PRE_MAX, "control_tokens"),
            "rupture_density": pooled_density(rows, *RUPTURE, "control_tokens"),
            "post1900_density": pooled_density(rows, 1901, 1950, "control_tokens"),
            "bootstrap_rupture_vs_pre": bootstrap_diff(rows, "control_tokens"),
        },
        "loyalist_full_lexicon": {
            "pre_density": pooled_density(rows_full, 1600, PRE_MAX, "loyalist_weighted"),
            "rupture_density": pooled_density(rows_full, *RUPTURE, "loyalist_weighted"),
            "post1900_density": pooled_density(rows_full, 1901, 1950, "loyalist_weighted"),
        },
        "changepoint": changepoint(rows),
    }

    # write yearly.csv
    import csv
    with (RES / "yearly.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["author", "year", "n_chars", "loyalist_density100",
                    "control_density100", "loyalist_entries"])
        for r in sorted(rows, key=lambda r: r["year"]):
            w.writerow([r["author"], r["year"], r["n_chars"],
                        f'{r["loyalist_density100"]:.3f}', f'{r["control_density100"]:.3f}',
                        r["loyalist_entries"]])
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    make_figure(rows, summary)

    # console report
    L, C = summary["loyalist"], summary["control"]
    print(f"sections={summary['n_sections']} authors={summary['authors']} "
          f"years={summary['year_range']}")
    print(f"LOYALIST  pre={L['pre_density']:.3f}  rupture={L['rupture_density']:.3f}  "
          f"post1900={L['post1900_density']:.3f}")
    print(f"CONTROL   pre={C['pre_density']:.3f}  rupture={C['rupture_density']:.3f}  "
          f"post1900={C['post1900_density']:.3f}")
    bL = L["bootstrap_rupture_vs_pre"]; bC = C["bootstrap_rupture_vs_pre"]
    if bL:
        print(f"LOYALIST rupture-pre diff = {bL['point']:.3f}  95%CI[{bL['ci_lo']:.3f},{bL['ci_hi']:.3f}]  p={bL['p_two_sided']:.4f}")
    if bC:
        print(f"CONTROL  rupture-pre diff = {bC['point']:.3f}  95%CI[{bC['ci_lo']:.3f},{bC['ci_hi']:.3f}]  p={bC['p_two_sided']:.4f}")
    if summary["changepoint"]:
        print(f"changepoint (loyalist series) at year {summary['changepoint']['changepoint_year']}")


if __name__ == "__main__":
    main()

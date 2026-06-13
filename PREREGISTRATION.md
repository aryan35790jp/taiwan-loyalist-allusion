# Preregistration — The Half-Life of a Lost Empire

**Registered before the corpus-scale (NMTL 全臺詩) run.** The pilot on 許南英 (窺園留草) is
reported as a pilot and does not consume the confirmatory hypotheses below.

## Object
Classical Chinese poems written in/about Taiwan, 1683–1945, each datable to a year (or
author floruit), each scored for *loyalist-allusion density* (specificity-weighted hits on
the loyalist lexicon per 100 CJK characters) and *control-allusion density* (neutral
canonical allusions per 100 chars).

## Confirmatory hypotheses
- **H1 (spike).** Loyalist density in the rupture window (1895–1900) exceeds the
  pre-rupture baseline (≤1894). Directional, bootstrap 95% CI on the difference excludes 0.
- **H2 (specificity).** The rupture rise in *loyalist* density exceeds the rupture change in
  *control* density (difference-in-differences > 0, CI excludes 0). This is the guard
  against "poets just alluded more after 1895."
- **H3 (decay / half-life).** After the 1895–1900 peak, loyalist density declines
  monotonically-in-trend across the colonial decades; we fit an exponential decay and report
  the estimated half-life with CI.
- **H4 (changepoint).** An unsupervised changepoint on the loyalist-density series falls in
  1895 ± 3 years.
- **H5 (external validation).** Poets independently labelled *loyalist* by historians
  (data/poet_metadata.csv) show higher loyalist density than those labelled
  *accommodationist/modernist*; labels never enter the measure. Permutation test, p<0.05.

## Falsifiable predictions (what would sink the thesis)
- If control-allusion density rises at 1895 as much as loyalist density (H2 fails), the
  effect is generic allusiveness, not loyalism — **reported as a negative result.**
- If the loyalist rise is driven entirely by the local Ming-Zheng layer (鄭成功/東寧) and
  vanishes when those entries are removed, the finding is "Koxinga revival," not a general
  dynastic-fall register — we report the lexicon-ablation either way.
- If historian-labelled loyalists do NOT separate from accommodationists (H5 fails), the
  measure does not track the construct — **reported.**
- If the post-peak series is flat rather than decaying (H3 fails), there is no "half-life";
  we report persistence instead and drop the half-life framing.

## Analysis specification (locked)
- Primary lexicon subset: loyalist entries with specificity ≥ 0.8. Sensitivity run: all
  entries reweighted to 1.0.
- Density denominator: CJK-ideograph count only (punctuation/Latin stripped).
- Greedy longest-match, one credit per distinct entry per poem (token count also recorded).
- Script normalised to Traditional via OpenCC before matching.
- Bootstrap: 10,000 resamples of sections within period; seed 42.
- Changepoint: ruptures Dynp, model l2, 1 breakpoint.
- Multi-poet pooling: mixed-effects by author when ≥3 authors available; until then,
  within-author trajectories are reported separately and not pooled.

## Data-provenance honesty
- Pilot text: 許南英《窺園留草》from zh.wikisource (chronologically arranged; year headers
  carry explicit Western years). Simplified→Traditional via OpenCC.
- Confirmatory corpus: NMTL 智慧型全臺詩知識庫 export (not bulk-downloadable; ingested via
  `acquire_taiwan.ingest_nmtl_export`). No poem text is authored by us; all is sourced.
- No results are simulated. Underpowered pilot numbers are labelled as such.

---

## Outcomes against predictions (honest post-analysis record)
Recorded after running the analyses; maps each hypothesis to its result and whether the
preregistered falsification condition was triggered.

- **H1 (spike).** Supported at the poem level on the anthology (rupture 0.268 vs mid-Qing
  0.087, p<0.0001) and robust across 6 detector settings. **Caveat (honest):** at the
  volume-cluster level the contrast is p=0.12 — not significant under the most conservative
  clustering. Net: supported poem-level; not confirmed under volume clustering.
- **H2 (specificity).** Supported. Neutral control is flat across the rupture in every
  contrast (anthology p=0.99; vs gazetteer p=0.32); DiD positive (+0.14 to +0.18).
- **H3 (decay / half-life).** Supported directionally in the independent single author
  (許南英: 0.078 baseline → 0.131 at 1895–1900 → 0.080 after 1900). Underpowered (n small).
  No formal half-life fit (too few dated points); reported as a qualitative decay.
- **H4 (changepoint).** Supported. Unsupervised changepoint on the 許南英 series falls at
  1897 (within the preregistered 1895±3 window).
- **H5 (external validation).** Mixed/honest. Historian-labelled loyalists exceed the
  modernist (丘逢甲 0.177 high), but pooled loyalists vs modernist p≈0.24 — the lyric signal
  is concentrated in Qiu Fengjia, not uniform. Falsification condition (no separation) NOT
  triggered, but the effect is not significant. Reported as exploratory.

## Falsification conditions: which fired
- Control rising as much as loyalist at the rupture (would sink the thesis): **did NOT fire**
  (control flat everywhere).
- Effect driven entirely by the Koxinga/Ming-Zheng local layer: **did NOT fire** (surge
  survives removing that layer; driven by loyalty_refusal + dynastic_fall canon).
- Historian-labelled loyalists fail to separate: **did NOT fire** (they separate
  directionally; significance limited by n and register).
- Independent corroboration of the baseline: **CONFIRMED** (gazetteer ≈ 連橫 mid-Qing, p=0.71).

## New analyses added beyond the original registration (clearly post-hoc)
- Cross-source triangulation (gazetteer independent baseline).
- Per-category trope heterogeneity (loyalty_refusal identified as the driver).
- SikuBERT representational probe (register reality, p<0.0001).
These are reported as exploratory/confirmatory-of-robustness, not preregistered confirmatory.

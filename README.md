# The Half-Life of a Lost Empire

**Measuring the decay of loyalist (遺民) allusion in Taiwan classical poetry across the 1895 rupture, 1683–1945.**

## The claim
When the Qing ceded Taiwan to Japan in 1895, Taiwanese literati writing classical
Chinese verse reached for an inherited repertoire of *dynastic-fall and loyalist
allusion* (黍離, 採薇/首陽, 銅駝荊棘, 神州陸沉, 楚囚, 文天祥, 屈原, and — locally — the
Ming-loyalist Zheng/東寧 tradition). This project measures, year by year and cohort by
cohort, how that loyalist register **spiked at the 1895 rupture and then decayed** across
fifty years of Japanese rule — putting a number on the literary half-life of an imperial
loyalty, a question literary historians have so far argued only case by case.

## What is genuinely novel here (honest scope)
- Place-name / GIS mapping of the Taiwan poetry corpus has been done. **Thematic
  allusion-decay measurement has not.**
- The 遺民/loyalist reading of colonial Taiwan poetry is rich but **entirely qualitative**
  (e.g. Chien-hsin Tsai, *A Passage to China: Literature, Loyalism, and Colonial Taiwan*).
  We supply the first population-scale quantitative spine.
- We do **not** claim to discover that loyalist sentiment exists; we claim to *measure its
  trajectory* across a datable political rupture, with an auditable, annotation-free method,
  and to validate that the measure recovers historians' own labels of individual poets.

## The defensibility design (mirrors the lab's house method)
1. **Auditable lexicon, not cherry-picked.** The loyalist-allusion lexicon is built from
   the standard scholarly repertoire of dynastic-loss tropes, graded by loyalist
   specificity, with each entry sourced to its classical locus. See
   `data/lexicons/loyalist_allusions.json`.
2. **Frequency-matched control.** Loyalist allusion density is compared against a
   frequency-matched set of *neutral* canonical allusions (`control_allusions.json`). The
   loyalist signal must exceed the neutral baseline at 1895 — otherwise the spike is just a
   general "more allusion" effect.
3. **External validation.** Poets that historians independently label loyalist (遺民) vs.
   accommodationist/localist should separate on the loyalist index *without those labels
   ever entering the measure*. See `src/validate.py`.

## Data sources (and their access status from this build environment)
| Source | Content | Status here |
|---|---|---|
| NMTL 智慧型全臺詩知識庫 (`xdcm.nmtl.gov.tw`) | the authoritative *全臺詩* population, 1661–1945 | **unreachable from this sandbox**; pipeline ingests its export via `src/acquire_taiwan.py --nmtl-export` |
| ctext.org API | Taiwan gazetteers/anthologies w/ embedded poetry (e.g. 臺灣詩乘, 臺灣通史) | reachable |
| zh.wikisource | scattered individual Taiwan poems | reachable |
| chinese-poetry (GitHub) | 全唐詩/全宋詩 — canonical reference baseline | reachable |

**Honesty note:** headline corpus-scale numbers require the full NMTL 全臺詩 export, which a
researcher must obtain from NMTL / a library (it is not bulk-downloadable). Everything in
this repo runs end-to-end and produces real numbers on whatever corpus is supplied; the
included pilot uses only genuinely harvested public-domain poems and is labelled as a pilot.
No results are fabricated.

## Pipeline
```
src/acquire_canon.py       # (optional) canonical reference baseline
src/acquire_taiwan.py      # 許南英 窺園留草 -> dated within-poet sections; ingests NMTL export
src/acquire_cohort.py      # multi-poet author-works cohort (H5 validation)
src/acquire_anthology.py   # 連橫 臺灣詩乘 -> 997 marker-dated diachronic poems
src/acquire_gazetteer.py   # INDEPENDENT Qing-official gazetteer verse (selection-bias control)
src/verse.py               # classical regulated-verse detector (isolates poems from prose)
src/allusion_detect.py     # auditable loyalist/control allusion matcher (+category ablation)
src/analyze.py             # within-poet time series, 1895 changepoint, bootstrap
src/analyze_anthology.py   # diachronic density, rupture-vs-mid-Qing contrast, bimodal curve
src/ablation.py            # category-ablation robustness of the two peaks
src/analyze_crosssource.py # cross-source triangulation (gazetteer vs 連橫 vs 許南英)
src/validate.py            # H5 external validation (historian labels)
colab/sikubert_probe.py    # (GPU) representational probe; RUN_IN_COLAB.ipynb = one-click
```
See `FINDINGS.md` for all real results across five analyses and three independent corpora.

## Reproducibility
Deterministic with fixed seeds. Python 3.11. Dependencies: pandas, numpy, scipy,
ruptures, statsmodels, beautifulsoup4, lxml, jieba, requests, matplotlib.

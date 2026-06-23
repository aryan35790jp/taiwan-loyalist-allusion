# The Half-Life of a Lost Empire

Code and data for the paper *The Half-Life of a Lost Empire: Measuring the Decay of
Loyalist Allusion in Taiwan's Classical Poetry across the 1895 Rupture* (Aryan Maity).

Preprint: https://doi.org/10.5281/zenodo.20819359

## What this is

A transparent, lexicon-based study of loyalist allusion in classical Chinese poetry from
Taiwan. We score the density of dynastic-loss and loyalist figures across a corpus dated by
era and test whether the language of mourning rises at the 1895 cession. Every match is a
known figure with a known classical source, so the measurements can be checked by hand. A
representational probe with SikuBERT, which never saw the lexicon, is used as an independent
check.

## Repository layout

```
data/         the graded loyalist lexicon, the neutral control, and the dated corpora
src/          all acquisition, detection, and analysis code
results/      derived tables, figures, and summary files
colab/        the SikuBERT probe (runs on a free Colab GPU)
requirements.txt
```

Key scripts in `src/`:

- `acquire_anthology.py`, `acquire_gazetteer.py`, `acquire_cohort.py`, `acquire_pre1895.py`,
  `acquire_ctext.py`, `acquire_taiwan.py` — harvest the corpora from public sources
- `verse.py` — the verse detector that isolates regulated poems from gazetteer prose
- `allusion_detect.py` — exact, longest-match lexicon detection and density scoring
- `analyze.py`, `analyze_anthology.py`, `analyze_crosssource.py`,
  `analyze_indep_rupture.py`, `analyze_rigor.py` — the statistical analyses
- `ablation.py` — lexicon-layer ablations (detector-robustness table)
- `validate.py` — checks and sanity tests

The SikuBERT probe lives in `colab/` (`build_notebook.py`, `sikubert_probe.py`).

## Setup

```
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Reproduce the results

1. Acquire the corpora:
   ```
   python src/acquire_anthology.py
   python src/acquire_gazetteer.py
   python src/acquire_cohort.py
   ```
2. Run the detector and the analyses:
   ```
   python src/allusion_detect.py
   python src/analyze_anthology.py
   python src/analyze_crosssource.py
   python src/analyze_rigor.py
   python src/ablation.py
   ```
3. Run the SikuBERT probe from `colab/`.

All randomised procedures use a fixed seed, so the numbers reproduce exactly.

## The national corpus

The confirmatory population analysis needs the national 全臺詩 (Complete Taiwanese Poems)
database, which is not currently reachable online. The pipeline includes an ingestion path
so the analysis can be run unchanged once that corpus is available.

## License

Released under the MIT License (see `LICENSE`). Source texts are in the public domain or
quoted from openly available editions, as described in the paper.

## Citation

If you use this code or data, please cite the paper:

> Maity, Aryan. *The Half-Life of a Lost Empire: Measuring the Decay of Loyalist Allusion in
> Taiwan's Classical Poetry across the 1895 Rupture.* 2026. https://doi.org/10.5281/zenodo.20819359

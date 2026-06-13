# -*- coding: utf-8 -*-
"""
SikuBERT representational probe  (RUN ON GOOGLE COLAB, GPU runtime)
==================================================================
Purpose: an INDEPENDENT check that the loyalist-allusion register is linguistically real,
not an artefact of our keyword lexicon. We embed poems with a classical-Chinese transformer
(SikuBERT, trained on the 四庫全書) and ask:

  (P1) Do lexicon-loyalist poems vs lexicon-control poems separate in SikuBERT space better
       than chance?  -> logistic-probe 5-fold CV accuracy + silhouette, vs a label-shuffle null.
       If yes, the register is encoded in a model that never saw our lexicon.
  (P2) Is the separability HIGHER for rupture-era (>=1894) poems than mid-Qing poems?
       -> register sharpens at the rupture.

This is the ONLY GPU step in the project. The core paper does not depend on it; it is a
house-style representational corroboration.

HOW TO RUN
----------
1. New Colab notebook -> Runtime -> Change runtime type -> T4 GPU.
2. Upload data/raw/anthology_poems.jsonl (and optionally poems.jsonl) to the Colab session.
3. pip install: transformers torch scikit-learn  (Colab usually has torch already)
4. Paste this file into a cell (or %run it) and run.

Model: SIKU-BERT/sikubert  (fallback: ethanyt/guwenbert-base). Both are classical-Chinese BERTs.
"""
import json, numpy as np, torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import silhouette_score

MODEL = "SIKU-BERT/sikubert"          # fallback: "ethanyt/guwenbert-base"
MIN_SPEC = 0.8
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
RNG = np.random.default_rng(42)


# ---- minimal self-contained lexicon scorer (upload the two JSONs alongside) ----
def load_lex(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    forms = []
    for e in d["entries"]:
        spec = float(e.get("specificity", 1.0))
        for f in e["forms"]:
            forms.append((f, spec))
    forms.sort(key=lambda x: len(x[0]), reverse=True)
    return forms

def hits(text, forms, min_spec=0.0):
    return sum(1 for f, s in forms if s >= min_spec and f in text)

def label_poems(records, loy_forms, ctl_forms):
    """Label each poem loyalist(1)/control(0) by which register dominates; drop ties/empties."""
    X, y, era = [], [], []
    for r in records:
        t = r["text"]
        L = hits(t, loy_forms, MIN_SPEC); C = hits(t, ctl_forms)
        if L > C and L > 0:
            X.append(t); y.append(1); era.append(r.get("year_approx"))
        elif C > L and C > 0:
            X.append(t); y.append(0); era.append(r.get("year_approx"))
    return X, np.array(y), era

# ---- embeddings ----
def embed(texts, tok, model, bs=16, maxlen=128):
    vecs = []
    for i in range(0, len(texts), bs):
        batch = texts[i:i+bs]
        enc = tok(batch, padding=True, truncation=True, max_length=maxlen, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out = model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1)
        mean = (out * mask).sum(1) / mask.sum(1).clamp(min=1)
        vecs.append(mean.cpu().numpy())
    return np.vstack(vecs)

def probe(X, y, label=""):
    """5-fold CV logistic accuracy + silhouette, vs label-shuffle null."""
    clf = LogisticRegression(max_iter=2000)
    acc = cross_val_score(clf, X, y, cv=5, scoring="accuracy").mean()
    sil = silhouette_score(X, y) if len(set(y)) > 1 else float("nan")
    null = []
    for _ in range(200):
        yp = RNG.permutation(y)
        null.append(cross_val_score(clf, X, yp, cv=5, scoring="accuracy").mean())
    null = np.array(null)
    p = (null >= acc).mean()
    print(f"[{label}] n={len(y)} loyalist={int(y.sum())} control={int((1-y).sum())}")
    print(f"   CV acc={acc:.3f}  null={null.mean():.3f}±{null.std():.3f}  p={p:.4f}  silhouette={sil:.3f}")
    return {"n": len(y), "acc": float(acc), "null_mean": float(null.mean()),
            "p": float(p), "silhouette": float(sil)}


def _find_or_upload(fname):
    """Locate a required file in common Colab/local paths, else prompt an upload."""
    candidates = [fname, f"/content/{fname}",
                  f"/content/data/raw/{fname}", f"/content/data/lexicons/{fname}",
                  f"data/raw/{fname}", f"data/lexicons/{fname}"]
    for c in candidates:
        if Path(c).exists():
            return c
    try:
        from google.colab import files  # type: ignore
        print(f"\n>>> Please upload '{fname}' (file picker opening)...")
        up = files.upload()
        for name in up:
            if name == fname or name.endswith(fname):
                return name
        # if they uploaded under a different name, take the first
        if up:
            return list(up)[0]
    except Exception:
        pass
    raise FileNotFoundError(
        f"Could not find '{fname}'. Upload it to the Colab session "
        f"(from your repo: data/raw/anthology_poems.jsonl, "
        f"data/lexicons/loyalist_allusions.json, data/lexicons/control_allusions.json).")


def main():
    anthology = _find_or_upload("anthology_poems.jsonl")
    loy_path = _find_or_upload("loyalist_allusions.json")
    ctl_path = _find_or_upload("control_allusions.json")
    recs = [json.loads(l) for l in Path(anthology).read_text(encoding="utf-8").splitlines() if l.strip()]
    loy_forms = load_lex(loy_path)
    ctl_forms = load_lex(ctl_path)

    print(f"loading {MODEL} on {DEVICE} ...")
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL).to(DEVICE).eval()

    X_txt, y, era = label_poems(recs, loy_forms, ctl_forms)
    print(f"labelled {len(y)} poems")
    Xv = embed(X_txt, tok, model)

    results = {}
    # P1: register separability (all eras)
    results["P1_all"] = probe(Xv, y, "P1 loyalist-vs-control, all eras")

    # P2: rupture vs mid-Qing separability
    era = np.array([e if e is not None else -1 for e in era])
    rup = era >= 1894
    mid = (era >= 1700) & (era <= 1860)
    for name, mask in [("rupture>=1894", rup), ("mid-Qing 1700-1860", mid)]:
        idx = np.where(mask)[0]
        if len(set(y[idx])) > 1 and len(idx) > 30:
            results[f"P2_{name}"] = probe(Xv[idx], y[idx], f"P2 {name}")
        else:
            print(f"[P2 {name}] too few/one-class (n={len(idx)})")

    Path("sikubert_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nInterpretation:")
    print(" - P1 acc >> null (p<.05): the loyalist register is separable in a model that never")
    print("   saw our lexicon -> it is a real linguistic register, not a keyword artefact.")
    print(" - P2 rupture acc > mid-Qing acc: the register is sharper at the 1895 rupture.")


if __name__ == "__main__":
    main()

"""
allusion_detect.py
------------------
Auditable, lexicon-based allusion detection for classical Chinese poems.

Given a poem's text, count matches against:
  - the loyalist-allusion lexicon (specificity-weighted), and
  - the neutral control lexicon,
and normalise to a per-100-character density so poems of different length compare.

Design choices (all defensible / reportable):
  * Matching is exact substring on traditional-character surface forms. We deliberately
    avoid fuzzy or embedding matching so every hit is human-checkable.
  * To avoid double counting overlapping forms within one entry (e.g. '黍離' and '黍離麥秀'),
    we credit at most ONE hit per entry per poem for the primary 'presence' measure, and
    also keep a raw token-count measure. Both are reported.
  * Longer surface forms are matched first and their spans are consumed, so a hit on the
    4-gram '神州陸沉' is not also counted as the 2-gram '神州' / '陸沉'.

This module has no I/O side effects; analyze.py drives it over a corpus.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

LEX_DIR = Path(__file__).resolve().parent.parent / "data" / "lexicons"

# Strip everything that is not a CJK ideograph for length normalisation & matching.
_CJK = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")


def cjk_only(text: str) -> str:
    return "".join(_CJK.findall(text or ""))


@dataclass
class LexEntry:
    id: str
    forms: tuple[str, ...]
    category: str
    specificity: float = 1.0  # 1.0 for control entries (unused in their weighting)


@dataclass
class Lexicon:
    name: str
    entries: list[LexEntry]
    # forms sorted longest-first for greedy, non-overlapping matching
    _ordered: list[tuple[str, LexEntry]] = field(default_factory=list)

    def __post_init__(self):
        pairs = []
        for e in self.entries:
            for f in e.forms:
                pairs.append((f, e))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._ordered = pairs


def load_lexicon(path: Path) -> Lexicon:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = []
    for e in data["entries"]:
        entries.append(
            LexEntry(
                id=e["id"],
                forms=tuple(e["forms"]),
                category=e.get("category", ""),
                specificity=float(e.get("specificity", 1.0)),
            )
        )
    return Lexicon(name=data["lexicon"], entries=entries)


def load_default_lexicons() -> tuple[Lexicon, Lexicon]:
    return (
        load_lexicon(LEX_DIR / "loyalist_allusions.json"),
        load_lexicon(LEX_DIR / "control_allusions.json"),
    )


@dataclass
class PoemHits:
    n_chars: int
    # presence: distinct entries hit (counted once each)
    entries_hit: dict[str, int]          # entry_id -> raw token count in poem
    weighted_presence: float             # sum of specificity over distinct entries hit
    raw_tokens: int                      # total matched tokens (greedy, non-overlapping)

    def density_presence_per100(self) -> float:
        return 100.0 * self.weighted_presence / self.n_chars if self.n_chars else 0.0

    def density_tokens_per100(self) -> float:
        return 100.0 * self.raw_tokens / self.n_chars if self.n_chars else 0.0


def detect(text: str, lex: Lexicon, min_specificity: float = 0.0,
           exclude_categories: tuple[str, ...] = ()) -> PoemHits:
    """Greedy non-overlapping match. Mask consumed spans so longer forms win.
    exclude_categories drops entries in those lexicon categories (for ablations)."""
    s = cjk_only(text)
    n = len(s)
    consumed = [False] * n
    entries_hit: dict[str, int] = {}
    raw_tokens = 0

    for form, entry in lex._ordered:
        if entry.specificity < min_specificity:
            continue
        if entry.category in exclude_categories:
            continue
        flen = len(form)
        start = 0
        while True:
            idx = s.find(form, start)
            if idx == -1:
                break
            if not any(consumed[idx:idx + flen]):
                for k in range(idx, idx + flen):
                    consumed[k] = True
                entries_hit[entry.id] = entries_hit.get(entry.id, 0) + 1
                raw_tokens += 1
                start = idx + flen
            else:
                start = idx + 1

    # weighted presence: each distinct entry contributes its specificity once
    id2spec = {e.id: e.specificity for e in lex.entries}
    weighted = sum(id2spec.get(eid, 1.0) for eid in entries_hit)
    return PoemHits(
        n_chars=n,
        entries_hit=entries_hit,
        weighted_presence=weighted,
        raw_tokens=raw_tokens,
    )


def score_poem(text: str, loyalist: Lexicon, control: Lexicon,
               min_specificity: float = 0.0,
               exclude_categories: tuple[str, ...] = ()) -> dict:
    L = detect(text, loyalist, min_specificity=min_specificity,
               exclude_categories=exclude_categories)
    C = detect(text, control)
    return {
        "n_chars": L.n_chars,
        "loyalist_weighted": L.weighted_presence,
        "loyalist_tokens": L.raw_tokens,
        "loyalist_entries": list(L.entries_hit.keys()),
        "loyalist_density100": L.density_presence_per100(),
        "control_weighted": C.weighted_presence,
        "control_tokens": C.raw_tokens,
        "control_entries": list(C.entries_hit.keys()),
        "control_density100": C.density_tokens_per100(),
    }


if __name__ == "__main__":
    loy, ctl = load_default_lexicons()
    # quick self-test on two hand-typed lines (illustrative only, not data)
    demo = [
        ("loyalist-heavy", "宰相有權能割地，孤臣無力可回天。扁舟去作鴟夷子，回首河山意黯然。"),
        ("neutral", "渭城朝雨浥輕塵，客舍青青柳色新。勸君更盡一杯酒，西出陽關無故人。"),
    ]
    for label, t in demo:
        print(label, score_poem(t, loy, ctl))

"""
verse.py
--------
Extract genuine classical regulated verse (近體詩) from mixed prose+poetry pages such as
gazetteer 藝文志 sections. A poem is a maximal run of clauses whose CJK lengths are
predominantly a single line length L in {5,7} (the canonical shi line), with >=4 such lines.
This isolates poems from memorials/essays without any manual annotation, and every extracted
span is human-checkable.
"""
from __future__ import annotations
import re

_CJK = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
_SPLIT = re.compile(r"[，。！？；、\n\r\u3000]+")
# strong classical-prose markers, rare inside regulated verse lines
_PROSE = set("矣也焉哉夫蓋故者歟耳乎兮乃皆是凡蒙據茲爰惟粵撰序跋誌纂輯")


def _cjk_len(s: str) -> int:
    return len(_CJK.findall(s))


def _prose_markers(s: str) -> int:
    return sum(1 for ch in s if ch in _PROSE)


def extract_verses(text: str, line_lens=(5, 7), min_lines=4, max_lines=24,
                   max_prose_per_line=0.2) -> list[str]:
    """Return poems as runs of clauses of EXACTLY one canonical line length L in {5,7},
    min_lines..max_lines lines, rejecting runs dense in classical-prose function words.
    The max_lines cap rejects long parallel-prose/賦 passages that mimic verse rhythm."""
    clauses = [c for c in _SPLIT.split(text) if c.strip()]
    lens = [_cjk_len(c) for c in clauses]
    poems = []
    i, n = 0, len(clauses)
    while i < n:
        if lens[i] in line_lens:
            L = lens[i]
            j = i
            run = []
            while j < n and lens[j] == L:
                run.append(j)
                j += 1
            if min_lines <= len(run) <= max_lines:
                poem = "".join(clauses[k] for k in run)
                if _prose_markers(poem) / len(run) <= max_prose_per_line:
                    poems.append(poem)
            i = j if len(run) else i + 1
        else:
            i += 1
    return poems


if __name__ == "__main__":
    # validation: a real poem (should be found) vs prose (should be rejected)
    poem = "海天東望夕茫茫，山勢川形闊復長。萬里波濤排碧落，千年版籍隸炎方。"
    prose = ("臺灣遠屬海外，民番雜處，習俗異宜。自入版圖以來，所有鳳山縣之熟番力力等十二社，"
             "諸羅縣之熟番蕭壠等社，俱各傾心向化，願同編氓。")
    print("poem  ->", extract_verses(poem))
    print("prose ->", extract_verses(prose))

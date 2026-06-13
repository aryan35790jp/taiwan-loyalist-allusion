"""
build_notebook.py
-----------------
Generate a SELF-CONTAINED Colab notebook (RUN_IN_COLAB.ipynb): the data files + lexicons +
probe code are embedded (base64), so the user uploads ONE file and clicks Runtime > Run all.
No separate data upload, no path errors.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "colab" / "RUN_IN_COLAB.ipynb"

FILES = {
    "anthology_poems.jsonl": ROOT / "data" / "raw" / "anthology_poems.jsonl",
    "poems.jsonl": ROOT / "data" / "raw" / "poems.jsonl",
    "loyalist_allusions.json": ROOT / "data" / "lexicons" / "loyalist_allusions.json",
    "control_allusions.json": ROOT / "data" / "lexicons" / "control_allusions.json",
}

# the probe logic, embedded as a clean self-contained module (reads files from cwd)
PROBE = ROOT / "colab" / "sikubert_probe.py"


def code_cell(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src}


def md_cell(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def main():
    blobs = {name: base64.b64encode(p.read_bytes()).decode("ascii")
             for name, p in FILES.items()}
    probe_src = PROBE.read_text(encoding="utf-8")

    cells = []
    cells.append(md_cell([
        "# Taiwan Loyalist-Allusion — SikuBERT representational probe\n",
        "**One-click run:** set a GPU runtime (Runtime ▸ Change runtime type ▸ **T4 GPU**), ",
        "then Runtime ▸ **Run all**. Everything (data, lexicons, code) is embedded below.\n"]))

    cells.append(code_cell(["# 1) install deps (Colab already has torch / sklearn / numpy)\n",
                            "!pip -q install transformers >/dev/null 2>&1\n",
                            "print('deps ready')\n"]))

    # data-writing cell
    data_lines = ["# 2) write embedded data files to the session\n",
                  "import base64\n", "BLOBS = {\n"]
    for name, b in blobs.items():
        data_lines.append(f"  {name!r}: {b!r},\n")
    data_lines += ["}\n",
                   "for _n,_b in BLOBS.items():\n",
                   "    open(_n,'wb').write(base64.b64decode(_b))\n",
                   "print('wrote', list(BLOBS))\n"]
    cells.append(code_cell(data_lines))

    # probe code cell (strip the local _find_or_upload; files are now in cwd)
    cells.append(code_cell(["# 3) probe code + run\n"] +
                           [l + "\n" for l in probe_src.splitlines()]))

    nb = {"cells": cells,
          "metadata": {"accelerator": "GPU",
                       "colab": {"provenance": []},
                       "kernelspec": {"name": "python3", "display_name": "Python 3"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 0}

    OUT.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({kb:.0f} KB)")


if __name__ == "__main__":
    main()

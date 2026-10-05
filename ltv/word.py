"""
The Word version of the report.

Writes a resolved copy of the document - narrative, generated tables, figure
captions - to `out/word_content.json`, which `tools/mkword.js` turns into a
.docx with one picture per figure.

The Word version is for reading and commenting on, so each sliced figure
appears as the view it opens on. The HTML report remains the one to use for
anything that needs the slicers.
"""
import json

from . import config as C
from . import content as content_mod
from . import tables as TB
from .model import Model


def build(m: Model, bands, path=None) -> str:
    """Resolve the report into a flat list of blocks a document can be built from."""
    path = path or (C.OUT / "word_content.json")
    blocks = content_mod.load()

    built = TB.build(m)
    used = [False] * len(built)

    def generated(head):
        for i, entry in enumerate(built):
            if entry is None or used[i] or list(entry[0]) != list(head):
                continue
            used[i] = True
            return entry
        return None

    out = []
    for block in blocks:
        kind = block[0]
        if kind == "table":
            entry = generated(block[2])
            head, rows = entry if entry else (block[2], block[3])
            out.append({"kind": "table", "label": block[1],
                        "head": list(head), "rows": [list(r) for r in rows]})
        elif kind == "figure":
            out.append({"kind": "figure", "number": block[1],
                        "title": block[2], "caption": block[3]})
        elif kind == "h2":
            out.append({"kind": "h2", "text": block[1]})
        elif kind == "h3":
            out.append({"kind": "h3", "number": block[1], "text": block[2]})
        elif kind == "sub":
            out.append({"kind": "sub", "text": block[1]})
        elif kind == "list":
            out.append({"kind": "list", "items": list(block[1])})
        elif kind == "takeaway":
            out.append({"kind": "takeaway", "label": block[2], "text": block[1]})
        elif kind in ("p", "note", "flag", "empty"):
            out.append({"kind": kind, "text": block[1]})

    summary = m.agency_summary()
    header = {
        "title": "Optimising Net Income and Net LTV",
        "eyebrow": "Germany · Face-to-face agency donors",
        "standfirst": "What we ask donors to give, who we ask, and what to do about it.",
        "stats": [
            [format(int(round(summary["donors"].sum())), ",d"),
             "donors acquired by agencies"],
            ["€%.1fm" % (summary["cost"].sum() / 1e6), "acquisition spend"],
            ["€%.1fm" % (bands["gross_income"].sum() / 1e6),
             "%d-year gross income" % (C.HORIZON_MONTHS // 12)],
            ["€%.1fm" % (bands["net_income"].sum() / 1e6),
             "%d-year net income" % (C.HORIZON_MONTHS // 12)],
        ],
        "theme": C.THEME,
        "palette": {"navy": C.NAVY, "red": C.RED, "mut": C.MUT,
                    "line": C.LINE, "light": C.LIGHT, "th": C.TABLE_HEAD},
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"header": header, "blocks": out},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    return str(path)

"""
The HTML report.

Assembles the narrative from `content.json` and the charts and tables from the
model, into one self-contained file. Because the numbers are generated rather
than typed, re-running the model updates every figure in the document at once.
"""
from . import charts as G
from . import config as C
from . import content as content_mod
from . import figures as F
from . import tables as TB
from . import theme as T
from .model import Model




def _table(head, rows, label="") -> str:
    lab = '<div class="tlab">%s</div>' % label if label else ""
    th = "".join("<th>%s</th>" % h for h in head)
    body = ""
    for r in rows:
        cls = ' class="tot"' if str(r[0]).lower().startswith(("total", "all ")) else ""
        body += "<tr%s>%s</tr>" % (cls, "".join("<td>%s</td>" % c for c in r))
    # A two- or three-column table stretched across the full width leaves the
    # numbers stranded away from the labels, so narrow tables size to content.
    cls = ' class="narrow"' if len(head) <= 3 else ''
    # A wide table scrolls sideways on a phone, so say so rather than letting
    # the reader wonder whether a column is missing.
    hint = ('<p class="hint">Scroll the table sideways to see every amount.</p>'
            if len(head) > 4 else "")
    return (lab + '<div class="tw" tabindex="0" role="region" aria-label="%s">'
            '<table%s><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></div>%s'
            % (label or "Table", cls, th, body, hint))


def _figure(number, title, caption, svg) -> str:
    # One label, so a figure reads the same in the report, in Word and in a
    # conversation about it: "Figure 7 - Donor net LTV (10 years)". The number
    # is a chip and the title is set as a title, so a reader skimming for a
    # chart finds it without reading the words.
    out = '<figure><div class="fhead"><span class="flab">Figure %d</span>' % number
    if title:
        out += '<span class="ftitle">%s</span>' % title
    out += "</div>"
    out += svg
    if caption:
        out += "<figcaption>%s</figcaption>" % caption
    return out + "</figure>"


def build(m: Model, blocks=None, path=None) -> str:
    """Assemble the report and return the path written."""
    blocks = blocks if blocks is not None else content_mod.load()
    path = path or (C.OUT / "report.html")

    bands = m.band_summary()
    agencies = m.agency_summary()

    # Figures the narrative already captions keep the written caption; the
    # rest carry the caption the figure generates for itself, which changes
    # with the slicer.
    captioned = {b[1] for b in blocks if b[0] == "figure" and b[3]}
    generated = F.build(m, bands, captioned)

    # Tables are generated too, matched to the narrative's own by their header
    # row and taken in order. A written table whose header no longer matches
    # anything the model produces is left exactly as written, so the report
    # never silently loses a table.
    built = TB.build(m)
    used = [False] * len(built)

    def _generated(head):
        for i, entry in enumerate(built):
            if entry is None or used[i] or list(entry[0]) != list(head):
                continue
            used[i] = True
            return entry
        return None

    # The contents list mirrors the document's own structure: a top-level
    # entry per part, the numbered findings nested beneath theirs.
    body, nav = [], []
    for block in blocks:
        kind = block[0]
        if kind == "h2":
            anchor = block[1].lower().replace(" ", "-")[:24]
            nav.append(("grp", anchor, block[1]))
            body.append('<h2 id="%s">%s</h2>' % (anchor, block[1]))
        elif kind == "h3":
            anchor = "s" + (block[1] or str(len(nav)))
            nav.append(("sub", anchor, "%s. %s" % (block[1], block[2])))
            body.append('<h3 id="%s"><span class="n" aria-hidden="true">%s</span>'
                        '<span>%s</span></h3>' % (anchor, block[1], block[2]))
        elif kind == "sub":
            body.append("<h4>%s</h4>" % block[1])
        elif kind == "p":
            body.append("<p>%s</p>" % block[1])
        elif kind == "note":
            body.append('<p class="note">%s</p>' % block[1])
        elif kind == "flag":
            body.append('<p class="flag">%s</p>' % block[1])
        elif kind == "takeaway":
            body.append('<p class="tk"><em>%s</em>%s</p>' % (block[2], block[1]))
        elif kind == "empty":
            body.append('<div class="empty">%s</div>' % block[1])
        elif kind == "list":
            body.append('<ul class="asm">%s</ul>'
                        % "".join("<li>%s</li>" % x for x in block[1]))
        elif kind == "table":
            entry = _generated(block[2])
            head, rows = entry if entry else (block[2], block[3])
            body.append(_table(head, rows, block[1]))
        elif kind == "figure":
            number, title, caption = block[1], block[2], block[3]
            svg = generated.get(number)
            if svg is None:
                svg = ('<div class="empty">Figure %d is not regenerated by the '
                       "model - see README.</div>" % number)
            body.append(_figure(number, title, caption, svg))

    donors = agencies["donors"].sum()
    stats = [
        (format(int(round(donors)), ",d"), "donors acquired by agencies"),
        ("€%.1fm" % (agencies["cost"].sum() / 1e6), "acquisition spend"),
        ("€%.1fm" % (bands["gross_income"].sum() / 1e6),
         "%d-year gross income" % (C.HORIZON_MONTHS // 12)),
        ("€%.1fm" % (bands["net_income"].sum() / 1e6),
         "%d-year net income" % (C.HORIZON_MONTHS // 12)),
    ]
    stat_html = ('<div class="statlab">2026 acquisition projections</div><div class="stats">'
                 + "".join('<div class="stat"><b>%s</b><span>%s</span></div>' % s
                           for s in stats) + "</div>")
    nav_html = "<ol>" + "".join(
        '<li class="%s"><a href="#%s">%s</a></li>' % n for n in nav) + "</ol>" 

    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Germany F2F - Optimising Net Income and Net LTV</title>
<style>%s%s</style></head><body>
<a class="skip" href="#report">Skip to the report</a>
<div class="prog" aria-hidden="true"></div>
<header class="top"><div class="inner">
<div class="eyebrow">Germany · Face-to-face agency donors</div>
<h1>Optimising Net Income and Net LTV</h1>
<p>What we ask donors to give, who we ask, and what to do about it.</p>
%s%s</div></header>
<div class="wrap">
<nav aria-label="Contents"><div class="lbl">Contents</div>%s</nav>
<main id="report">%s</main></div>
<footer>%s</footer>
<button class="totop" type="button" aria-label="Back to the top">&uarr;</button>
<script>%s%s</script>
</body></html>""" % (T.css(), G.SLICER_CSS, stat_html, T.logo_html(), nav_html,
                      "\n".join(body), T.footer(), G.SLICER_JS, T.PAGE_JS)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)

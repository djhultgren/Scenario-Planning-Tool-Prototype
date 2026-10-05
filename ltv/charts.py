"""
Charts, drawn as SVG.

No charting library. Every chart is built by working out pixel positions and
emitting SVG elements, which means the outputs are single self-contained files
with nothing to load from the internet and nothing to break when they are
emailed or opened offline.

Static charts are rendered here in Python. Interactive ones are drawn in the
browser by `assets/charts.js` from data this module exports as JSON - the
drawing logic is the same, it just runs in a different place.
"""
import json

from . import config as C

FONT = "font-family:inherit"


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def text(x, y, s, size=11.5, colour=None, anchor="start", bold=False):
    # Resolved when the label is drawn, not when this module is imported, so a
    # theme switch reaches the charts.
    colour = colour or C.MUT
    return ('<text x="%.1f" y="%.1f" font-size="%s" fill="%s" text-anchor="%s"%s>%s</text>'
            % (x, y, size, colour, anchor, ' font-weight="700"' if bold else "", _esc(s)))


def rect(x, y, w, h, colour, r=3):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s"/>'
            % (x, y, max(w, 0), max(h, 0), r, colour))


def line(x1, y1, x2, y2, colour=None, dash=None):
    colour = colour or C.LINE
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    return ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"%s/>'
            % (x1, y1, x2, y2, colour, d))


def svg(width, height, body) -> str:
    return ('<svg viewBox="0 0 %d %d" width="100%%" style="height:auto;'
            'overflow:visible;%s">%s</svg>' % (width, height, FONT, body))


def money(v) -> str:
    return "€" + format(int(round(v)), ",d")


# ------------------------------------------------------------- volumes -----
def volumes_by_band(summary) -> str:
    """Horizontal bars: how many donors we acquire at each gift amount."""
    bands = [b for b in C.BAND_ORDER if b in summary.index]
    W, H, L, R, T, B = 880, 336, 76, 230, 16, 42
    pw, ph = W - L - R, H - T - B
    total = summary["donors"].sum()
    mx = summary["donors"].max() * 1.02
    rh = ph / len(bands)
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for i, band in enumerate(bands):
        y = T + rh * i + rh * 0.20
        v = float(summary.loc[band, "donors"])
        out.append(rect(L, y, pw * v / mx, rh * 0.56, C.BAND_COLOUR[band], 4))
        share = 100 * v / total
        out.append(text(L + pw * v / mx + 10, y + rh * 0.42,
                        "%s   %s" % (format(int(round(v)), ",d"),
                                     ("%.1f%%" % share) if share < 1 else ("%.0f%%" % share)),
                        12, C.NAVY, bold=True))
        out.append(text(L - 12, y + rh * 0.42, band, 12.5, C.NAVY, "end", True))
    return svg(W, H, "".join(out))


# ----------------------------------------------------------- LTV by band ---
def ltv_by_band(summary, column="gross_ltv", low_base=None) -> str:
    """Horizontal bars of lifetime value, with thin bands faded."""
    bands = [b for b in C.BAND_ORDER if b in summary.index]
    W, H, L, R, T, B = 880, 336, 76, 150, 16, 42
    pw, ph = W - L - R, H - T - B
    mx = summary[column].max() * 1.04
    rh = ph / len(bands)
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for i, band in enumerate(bands):
        y = T + rh * i + rh * 0.20
        v = float(summary.loc[band, column])
        thin = low_base is not None and summary.loc[band, "historic_n"] < low_base
        out.append(rect(L, y, pw * max(v, 0) / mx, rh * 0.56,
                        C.BAND_COLOUR[band], 4))
        lbl = money(v) + ("   low base" if thin else "")
        out.append(text(L + pw * max(v, 0) / mx + 10, y + rh * 0.42, lbl,
                        12, C.NAVY, bold=True))
        out.append(text(L - 12, y + rh * 0.42, band, 12.5, C.NAVY, "end", True))
    return svg(W, H, "".join(out))


# ------------------------------------------------------ retention curves ---
def retention_curves(curves: dict[str, list[float]], months=C.HORIZON_MONTHS) -> str:
    """
    Survival curves by gift band.

    Solid to month 60 where the data is observed, dashed beyond where it is
    projected, with the divide marked so nobody mistakes one for the other.
    """
    W, H, L, R, T, B = 880, 392, 64, 150, 32, 48
    pw, ph = W - L - R, H - T - B
    px = lambda mth: L + pw * mth / months
    py = lambda v: T + ph * (1 - v / 100.0)
    out = [rect(0, 0, W, H, "#fff", 0)]
    for g in range(0, 101, 20):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, "%d%%" % g, 10.5, C.MUT, "end"))
    for mth in (0, 12, 24, 36, 48, 60, 84, 120):
        if mth <= months:
            out.append(text(px(mth), T + ph + 18, mth, 10.5, C.MUT, "middle"))
    out.append(text(L + pw / 2, H - 6, "Months since sign-up", 11, C.MUT, "middle"))
    out.append(line(px(C.OBSERVED_MONTHS), T, px(C.OBSERVED_MONTHS), T + ph,
                    C.LINE, "4 3"))
    out.append(text(px(C.OBSERVED_MONTHS) - 7, T + 11, "observed", 10, C.MUT, "end", True))
    out.append(text(px(C.OBSERVED_MONTHS) + 7, T + 11, "projected", 10, C.MUT))

    ends = []
    for band, curve in curves.items():
        colour = C.BAND_COLOUR.get(band, C.MUT)
        pts = [(m, 100 * curve[m]) for m in range(0, months + 1, 3)]
        obs = [p for p in pts if p[0] <= C.OBSERVED_MONTHS]
        prj = [p for p in pts if p[0] >= C.OBSERVED_MONTHS]
        for seg, dash in ((obs, None), (prj, "5 4")):
            d = " ".join(("M" if j == 0 else "L") + "%.1f %.1f" % (px(m), py(v))
                         for j, (m, v) in enumerate(seg))
            out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4"%s/>'
                       % (d, colour, ' stroke-dasharray="%s"' % dash if dash else ""))
        ends.append([py(100 * curve[months]), band, 100 * curve[12], 100 * curve[months]])

    ends.sort()
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 14:
            ends[k][0] = ends[k - 1][0] + 14
    for y0, band, r12, rend in ends:
        colour = C.BAND_COLOUR.get(band, C.MUT)
        out.append(text(L + pw + 10, y0, "%s   %.0f%% → %.0f%%" % (band, r12, rend),
                        11, colour, bold=True))
    return svg(W, H, "".join(out))


# --------------------------------------------------------- agency compare --
def agency_cpa_vs_ltv(summary) -> str:
    """Paired bars: what each agency costs against what their donors return."""
    agencies = list(summary.index)
    W, H, L, R, T, B = 880, 300, 64, 20, 20, 54
    pw, ph = W - L - R, H - T - B
    mx = max(summary["avg_cpa"].max(), summary["net_ltv"].max()) * 1.16
    bw = pw / len(agencies)
    py = lambda v: T + ph * (1 - v / mx)
    out = [rect(0, 0, W, H, "#fff", 0)]
    for g in range(0, int(mx) + 1, 100):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, money(g), 10.5, C.MUT, "end"))
    for i, a in enumerate(agencies):
        x0, w = L + bw * i + bw * 0.18, bw * 0.29
        cpa = float(summary.loc[a, "avg_cpa"])
        net = float(summary.loc[a, "net_ltv"])
        out.append(rect(x0, py(cpa), w, T + ph - py(cpa), C.RED))
        out.append(text(x0 + w / 2, py(cpa) - 6, money(cpa), 11, C.RED, "middle", True))
        out.append(text(x0 + w / 2, py(cpa) + 17, "CPA", 10.5, "#fff", "middle", True))
        out.append(rect(x0 + w + 5, py(net), w, T + ph - py(net), C.NAVY))
        out.append(text(x0 + w + 5 + w / 2, py(net) - 6, money(net), 11, C.NAVY, "middle", True))
        out.append(text(x0 + w + 5 + w / 2, py(net) + 17, "Net LTV", 10.5, "#fff", "middle", True))
        out.append(text(x0 + w + 5 + w / 2, py(net) + 30, "10y", 10.5, "#fff", "middle", True))
        out.append(text(L + bw * i + bw / 2, T + ph + 18, a, 12.5, C.NAVY, "middle", True))
        out.append(text(L + bw * i + bw / 2, T + ph + 32,
                        "%s donors · ×%.2f%s"
                        % (format(int(summary.loc[a, "donors"]), ",d"),
                           summary.loc[a, "cpa_factor"],
                           " capped" if summary.loc[a, "capped"] else ""),
                        10, C.MUT, "middle"))
    return svg(W, H, "".join(out))


def export_json(obj) -> str:
    """Serialise model output for the in-browser charts."""
    return json.dumps(obj, ensure_ascii=False, default=float)


# ==========================================================================
# Sliced figures
#
# A sliced figure is several charts in one: every view is drawn up front and
# the page shows one at a time. Nothing is computed in the browser, so what
# a reader sees is exactly what the model produced, and the page still works
# offline and when emailed.
# ==========================================================================
SLICER_CSS = """
.slicer{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.slicer button{font:inherit;font-size:12.5px;font-weight:700;cursor:pointer;
 padding:5px 12px;border-radius:999px;border:1px solid var(--line);
 background:#fff;color:var(--mut);line-height:1.3}
.slicer button:hover{border-color:var(--red);color:var(--red)}
.slicer button.on{background:var(--red);border-color:var(--red);color:#fff}
.states>.st{display:none}.states>.st.on{display:block}
@media print{.slicer{display:none}.states>.st{display:block}
 .states>.st:not(.on){display:none}}
"""

SLICER_JS = """
document.querySelectorAll('.slicer').forEach(function(bar){
 var g=bar.getAttribute('data-g');
 bar.addEventListener('click',function(e){
  var b=e.target.closest('button');if(!b)return;
  Array.prototype.forEach.call(bar.children,function(x){
   x.classList.toggle('on',x===b);});
  document.querySelectorAll('.states[data-g="'+g+'"]>.st').forEach(function(d){
   d.classList.toggle('on',d.getAttribute('data-k')===b.getAttribute('data-k'));});
 });
});
"""


def sliced(group: str, states: list) -> str:
    """
    Assemble one sliced figure.

    `states` is a list of (key, title, svg, caption). The first is the one
    shown when the page opens.
    """
    buttons = "".join(
        '<button data-k="%s"%s>%s</button>'
        % (_esc(k), ' class="on"' if i == 0 else "", _esc(k))
        for i, (k, _, _, _) in enumerate(states))
    panels = ""
    for i, (key, title, body, caption) in enumerate(states):
        panels += ('<div class="st%s" data-k="%s">%s%s%s</div>'
                   % (" on" if i == 0 else "", _esc(key),
                      '<div class="ttl">%s</div>' % title if title else "",
                      body,
                      "<figcaption>%s</figcaption>" % caption if caption else ""))
    return ('<div class="slicer" data-g="%s">%s</div>'
            '<div class="states" data-g="%s">%s</div>' % (group, buttons, group, panels))


# ------------------------------------------------- lifetime value by band ---
def ltv_bars(values: dict, counts: dict, mx: float, thin_below: int) -> str:
    """
    Horizontal lifetime-value bars, one row per gift amount.

    Bands with no donors in the slice say so rather than vanishing, and bands
    resting on few historic donors are faded and labelled, so a reader can
    see at a glance which bars carry weight.
    """
    bands = list(C.BAND_ORDER)
    W, H, L, R, T, B = 880, 336, 76, 150, 16, 42
    pw, ph = W - L - R, H - T - B
    rh = ph / len(bands)
    px = lambda v: L + pw * max(v, 0) / mx
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for i, band in enumerate(bands):
        y = T + rh * i + rh * 0.20
        out.append(text(L - 12, y + rh * 0.42, band, 12.5, C.NAVY, "end", True))
        v = values.get(band)
        if v is None:
            out.append(text(L + 6, y + rh * 0.42, "no donors in this age band",
                            11.5, C.MUT))
            continue
        thin = counts.get(band, 0) < thin_below
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" '
                   'fill="%s"%s/>' % (L, y, max(px(v) - L, 1), rh * 0.56,
                                      C.BAND_COLOUR[band],
                                      ' opacity="0.45"' if thin else ""))
        out.append(text(px(v) + 10, y + rh * 0.42, money(v), 12, C.NAVY, bold=True))
        if thin:
            out.append(text(px(v) + 12 + len(money(v)) * 7.2, y + rh * 0.42,
                            "low base", 10.5, C.MUT))
    return svg(W, H, "".join(out))


# ------------------------------------------------------ retention by band ---
def retention_lines(curves: dict, counts: dict, thin_below: int,
                    months=C.HORIZON_MONTHS) -> str:
    """
    Survival curves by gift amount, with the observed window marked.

    Solid to month 60 where we have data, dashed beyond it where the model is
    projecting. The label on the right carries both ends of the story: where
    the band stands at twelve months and where it lands at ten years.
    """
    W, H, L, R, T, B = 880, 392, 64, 178, 32, 48
    pw, ph = W - L - R, H - T - B
    px = lambda mth: L + pw * mth / months
    py = lambda v: T + ph * (1 - v / 100.0)
    out = [rect(0, 0, W, H, "#fff", 0)]
    for g in range(0, 101, 20):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, "%d%%" % g, 10.5, C.MUT, "end"))
    for mth in (0, 12, 24, 36, 48, 60, 84, 120):
        if mth <= months:
            out.append(text(px(mth), T + ph + 18, mth, 10.5, C.MUT, "middle"))
    out.append(text(L + pw / 2, H - 6, "Months since sign-up", 11, C.MUT, "middle"))
    obs = C.OBSERVED_MONTHS
    out.append(line(px(obs), T, px(obs), T + ph, C.MUT, "4 3"))
    out.append(text(px(obs) - 7, T + 11, "observed", 10, C.MUT, "end", True))
    out.append(text(px(obs) + 7, T + 11, "projected", 10, C.MUT))
    out.append(line(px(12), T + 4, px(12), T + ph, C.MUT, "3 3"))
    out.append(text(px(12), T - 1, "12 months", 10, C.MUT, "middle", True))

    ends = []
    for band, curve in curves.items():
        colour = C.BAND_COLOUR.get(band, C.MUT)
        pts = [(m, 100.0 * curve[m]) for m in range(0, months + 1)]
        solid = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", px(m), py(v))
                         for i, (m, v) in enumerate(pts[:obs + 1]))
        dashed = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", px(m), py(v))
                          for i, (m, v) in enumerate(pts[obs:]))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4" '
                   'stroke-linecap="round"/>' % (solid, colour))
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4" '
                   'stroke-dasharray="5 4"/>' % (dashed, colour))
        out.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="#fff" stroke="%s" '
                   'stroke-width="2"/>' % (px(12), py(100 * curve[12]), colour))
        ends.append([py(100 * curve[months]), band, 100 * curve[12],
                     100 * curve[months], colour])
    # By ten years the curves have converged, so their end labels would pile up
    # on top of each other. Spread them down the right-hand margin in value
    # order and join each to its curve with a faint leader that starts clear of
    # the plot, so a leader is never mistaken for the curve falling away.
    ends.sort(key=lambda e: e[0])
    if ends:
        gap = max(15.0, min(20.0, ph / max(len(ends), 1)))
        span = gap * (len(ends) - 1)
        top = max(T + 10, min(ends[0][0], T + ph - span))
        for i, e in enumerate(ends):
            e.append(top + gap * i)
    for _, band, v12, vend, colour, y in ends:
        low = "  (low base)" if counts.get(band, 0) < thin_below else ""
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="1" opacity="0.35"/>'
                   % (L + pw + 3, py(vend), L + pw + 11, y - 4, colour))
        out.append(text(L + pw + 14, y, "%s   %d%% → %d%%%s"
                        % (band, round(v12), round(vend), low), 11, colour, bold=True))
    return svg(W, H, "".join(out))


# --------------------------------------------------------- agency compare ---
def agency_bars(rows: list, mx: float) -> str:
    """
    What each agency charges against what their donor is worth.

    `rows` is a list of (agency, cpa, net or None, subtitle). Where an agency
    barely acquires at the amount on show, the net bar is withheld rather than
    drawn from a handful of donors.
    """
    W, H, L, R, T, B = 830, 300, 64, 20, 20, 54
    pw, ph = W - L - R, H - T - B
    bw = pw / max(len(rows), 1)
    py = lambda v: T + ph * (1 - v / mx)
    out = [rect(0, 0, W, H, "#fff", 0)]
    for g in range(0, int(mx) + 1, 200):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, money(g), 10.5, C.MUT, "end"))
    for i, (agency, cpa, net, sub) in enumerate(rows):
        x0 = L + bw * i + bw * 0.18
        w = bw * 0.29
        out.append(rect(x0, py(cpa), w, T + ph - py(cpa), C.RED, 3))
        out.append(text(x0 + w / 2, py(cpa) - 6, money(cpa), 11, C.RED, "middle", True))
        out.append(text(x0 + w / 2, py(cpa) + 17, "CPA", 10.5, "#fff", "middle", True))
        xn = x0 + w + 5
        if net is None:
            out.append(rect(xn, T + ph - 3, w, 3, C.LINE, 1))
            out.append(text(xn + w / 2, T + ph - 12, "too few", 10, C.MUT, "middle"))
            out.append(text(xn + w / 2, T + ph - 1, "donors", 10, C.MUT, "middle"))
        else:
            out.append(rect(xn, py(net), w, T + ph - py(net), C.NAVY, 3))
            out.append(text(xn + w / 2, py(net) - 6, money(net), 11, C.NAVY,
                            "middle", True))
            out.append(text(xn + w / 2, py(net) + 17, "Net LTV", 10.5, "#fff",
                            "middle", True))
            out.append(text(xn + w / 2, py(net) + 30, "10y", 10.5, "#fff",
                            "middle", True))
        out.append(text(L + bw * i + bw / 2, T + ph + 18, agency, 12.5, C.NAVY,
                        "middle", True))
        out.append(text(L + bw * i + bw / 2, T + ph + 32, sub, 10, C.MUT, "middle"))
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- fee cap ---
def cap_steps(rows: list, cap: float) -> str:
    """
    What each step above the cap is worth, and what it would cost.

    `rows` is a list of (gift, extra income, extra fee without the cap). The
    fee under the cap is always nothing, which is the whole point: the agency
    is paid the same whether the donor gives the cap or twice it.
    """
    W, H, L, R, T, B = 830, 330, 70, 20, 54, 58
    pw, ph = W - L - R, H - T - B
    mx = max([r[1] for r in rows] + [r[2] for r in rows] + [1]) * 1.18
    bw = pw / max(len(rows), 1)
    py = lambda v: T + ph * (1 - v / mx)
    out = [rect(0, 0, W, H, "#fff", 0)]
    step = max(50, int(mx / 5 // 50) * 50)
    for g in range(0, int(mx) + 1, step):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, money(g), 10.5, C.MUT, "end"))
    for i, (gift, income, fee_full) in enumerate(rows):
        gw = bw * 0.74
        w = gw / 3
        x = L + bw * i + (bw - gw) / 2
        for j, (v, colour, lbl) in enumerate((
                (income, C.GREEN, "extra income"),
                (0.0, C.RED, "extra fee, capped"),
                (fee_full, C.MUT, "fee without the cap"))):
            xb = x + w * j
            h = T + ph - py(v)
            out.append(rect(xb, py(v), w * 0.86, max(h, 2), colour, 3))
            out.append(text(xb + w * 0.43, py(v) - 6, money(v), 10.5, colour,
                            "middle", True))
        out.append(text(L + bw * i + bw / 2, T + ph + 20, "€%d a month" % gift,
                        12, C.NAVY, "middle", True))
    out.append(text(L, T - 30, "Each bar: what one donor above the €%d cap adds "
                    "over ten years, and what the agency is paid for it"
                    % cap, 11.5, C.MUT))
    key = [("extra income", C.GREEN), ("extra fee, capped", C.RED),
           ("fee without the cap", C.MUT)]
    for j, (lbl, colour) in enumerate(key):
        kx = L + j * 200
        out.append(rect(kx, H - 26, 11, 11, colour, 2))
        out.append(text(kx + 16, H - 17, lbl, 10.5, C.MUT))
    return svg(W, H, "".join(out))


# --------------------------------------------------------------- headroom ---
def headroom(levels: list, need: dict, shares: dict, base: str,
             base_income: float) -> str:
    """
    How many donors each amount would take to raise what the main ask raises.

    Fewer is better, so a dot to the left of the line is a gain. This is the
    chart that answers "what would we give up by asking for more?" in the only
    currency that matters - donors.
    """
    BASE = 1000
    mx = max(list(need.values()) + [BASE]) * 1.14
    W, rh, L, R, T, B = 830, 72, 176, 76, 40, 44
    H = T + rh * max(len(levels), 1) + B
    pw = W - L - R
    px = lambda v: L + pw * v / mx
    out = []
    step = max(250, int(mx / 6 // 250) * 250)
    for g in range(0, int(mx) + 1, step):
        out.append(line(px(g), T - 10, px(g), T + rh * len(levels)))
        out.append(text(px(g), T + rh * len(levels) + 20,
                        format(g, ",d"), 10.5, C.MUT, "middle"))
    out.append(line(px(BASE), T - 16, px(BASE), T + rh * len(levels), C.MUT, "4 3"))
    out.append(text(px(BASE), T - 22, "1,000 donors at %s" % base, 11, C.NAVY,
                    "middle", True))
    for i, level in enumerate(levels):
        y = T + rh * i + rh * 0.52
        n = need[level]
        same = abs(n - BASE) < 1
        better = n < BASE
        colour = C.NAVY if same else (C.GREEN if better else C.RED)
        if not same:
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                       'stroke-width="9" stroke-linecap="round" opacity="0.35"/>'
                       % (px(min(n, BASE)), y, px(max(n, BASE)), y, colour))
        out.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s"/>'
                   % (px(BASE), y, C.NAVY))
        if not same:
            out.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s"/>'
                       % (px(n), y, colour))
            mid = (px(min(n, BASE)) + px(max(n, BASE))) / 2
            pct = round(abs(100 * (n / BASE - 1)))
            out.append(text(mid, y - 17, "%d%% %s" % (pct, "fewer" if better else "more"),
                            13, colour, "middle", True))
        else:
            out.append(text(px(BASE) + 14, y + 5, "their main ask", 12, C.NAVY,
                            bold=True))
        out.append(text(L - 16, y - 4, level, 14, C.NAVY, "end", True))
        share = shares.get(level, 0.0)
        out.append(text(L - 16, y + 14, "%s%% of their donors"
                        % (("%.1f" % share) if share < 10 else ("%.0f" % share)),
                        11, C.MUT, "end"))
    return svg(W, H, "".join(out))


# ------------------------------------------------------ retention reserve ---
def reserve(rows: list) -> str:
    """
    How much retention a higher ask could lose and still come out ahead.

    The navy dot is what the higher amount actually retains at twelve months;
    the red dot is the point where it stops beating the agency's main ask on
    ten-year net value. The gap between them is the margin for error.
    """
    W, rh, L, R, T, B = 830, 76, 176, 86, 40, 46
    H = T + rh * max(len(rows), 1) + B
    pw, mx = W - L - R, 90
    px = lambda v: L + pw * v / mx
    out = []
    for g in range(0, mx + 1, 10):
        out.append(line(px(g), T - 10, px(g), T + rh * len(rows)))
        out.append(text(px(g), T + rh * len(rows) + 20, "%d%%" % g, 10.5,
                        C.MUT, "middle"))
    for i, (hi, lo, hi_r, be_r) in enumerate(rows):
        y = T + rh * i + rh * 0.5
        pts = round(hi_r - be_r)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                   'stroke-width="10" stroke-linecap="round" opacity="0.4"/>'
                   % (px(be_r), y, px(hi_r), y, C.GREEN))
        out.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s"/>' % (px(be_r), y, C.RED))
        out.append('<circle cx="%.1f" cy="%.1f" r="8" fill="%s"/>' % (px(hi_r), y, C.NAVY))
        out.append(text((px(be_r) + px(hi_r)) / 2, y - 18,
                        "%d %s to spare" % (pts, "pt" if pts == 1 else "pts"),
                        13, C.GREEN, "middle", True))
        out.append(text(px(hi_r) + 14, y + 5, "%d%%" % round(hi_r), 12, C.NAVY, bold=True))
        out.append(text(px(be_r) - 14, y + 5, "%d%%" % round(be_r), 12, C.RED,
                        "end", True))
        out.append(text(L - 18, y - 4, hi, 14, C.NAVY, "end", True))
        out.append(text(L - 18, y + 15, "instead of %s" % lo, 11, C.MUT, "end"))
    return svg(W, H, "".join(out))


# ------------------------------------------------------- what we modelled ---
def behaviour_panel(rows: list) -> str:
    """
    One column per gift amount: who we acquire, and how they behave.

    Volumes and age describe the donors we are acquiring now; retention and
    upgrades describe how donors at that amount have behaved historically.
    Keeping both on one panel makes the seam between them visible.
    """
    labels = ["2026 donors", "Avg age", "12m retention", "Upgrade rate",
              "Avg upgrade"]
    W, L, T = 880, 132, 34
    cw = (W - L - 14) / max(len(rows), 1)
    rh = 30
    H = T + rh * (len(labels) + 1) + 16
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for j, lbl in enumerate(labels):
        out.append(text(L - 14, T + rh * (j + 1) + rh * 0.66, lbl, 11.5,
                        C.MUT, "end"))
    for i, row in enumerate(rows):
        x = L + cw * i
        out.append(rect(x + 3, T - 2, cw - 6, rh * 0.94, C.BAND_COLOUR.get(row["band"], C.MUT), 5))
        out.append(text(x + cw / 2, T + rh * 0.62, row["band"], 12.5, "#fff",
                        "middle", True))
        cells = [
            format(int(round(row["donors"])), ",d"),
            "%d" % round(row["age"]) if row["age"] else "—",
            "%d%%" % round(row["r12"] * 100),
            "%.1f%%" % (row["uprate"] * 100),
            "€%.2f" % row["upamt"],
        ]
        out.append(text(x + cw / 2, T + rh * 1.62 - 13,
                        "%s%% of donors" % (("%.1f" % row["share"]) if row["share"] < 1
                                            else ("%.0f" % row["share"])),
                        9.5, C.MUT, "middle"))
        for j, cell in enumerate(cells):
            out.append(text(x + cw / 2, T + rh * (j + 1) + rh * 0.66, cell, 12,
                            C.NAVY, "middle", True))
    return svg(W, H, "".join(out))


# ------------------------------------------------------------ age profile ---
def age_panel(rows: list) -> str:
    """
    Retention and value side by side, by age at sign-up.

    The bar is twelve-month retention, the figure beneath it is ten-year gross
    value. They rise together, which is the argument of the whole section.
    """
    W, H, L, R, T, B = 880, 330, 60, 20, 26, 74
    pw, ph = W - L - R, H - T - B
    bw = pw / max(len(rows), 1)
    py = lambda v: T + ph * (1 - v / 100.0)
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for g in range(0, 101, 20):
        out.append(line(L, py(g), L + pw, py(g)))
        out.append(text(L - 9, py(g) + 4, "%d%%" % g, 10.5, C.MUT, "end"))
    for i, row in enumerate(rows):
        x = L + bw * i + bw * 0.24
        w = bw * 0.52
        v = row["r12"] * 100
        out.append(rect(x, py(v), w, T + ph - py(v), C.NAVY, 4))
        out.append(text(x + w / 2, py(v) - 7, "%d%%" % round(v), 12, C.NAVY,
                        "middle", True))
        out.append(text(x + w / 2, T + ph + 20, money(row["gross"]), 13, C.RED,
                        "middle", True))
        out.append(text(x + w / 2, T + ph + 38, row["ab"], 12.5, C.NAVY,
                        "middle", True))
        out.append(text(x + w / 2, T + ph + 53, "%d%% of donors" % round(row["share"] * 100),
                        10.5, C.MUT, "middle"))
    out.append(text(L, T - 10, "12m retention", 11, C.NAVY, bold=True))
    out.append(text(L + pw, T - 10, "Gross LTV (10y)", 11, C.RED, "end", True))
    return svg(W, H, "".join(out))


# ---------------------------------------------------------------- payback ---
def payback(rows: list, months=C.HORIZON_MONTHS) -> str:
    """
    How long a donor takes to cover the fee we paid to acquire them.

    `rows` is a list of (band, months to break even, return multiple). Shorter
    is better; the multiple at the end says what the donor goes on to return
    on that fee over the full ten years.
    """
    W, rh, L, R, T, B = 880, 52, 76, 210, 36, 46
    H = T + rh * max(len(rows), 1) + B
    pw = W - L - R
    mx = max([r[1] for r in rows] + [12]) * 1.12
    px = lambda v: L + pw * v / mx
    out = [rect(0, 0, W, H, C.LIGHT, 8)]
    for g in range(0, int(mx) + 1, 6):
        out.append(line(px(g), T - 8, px(g), T + rh * len(rows)))
        out.append(text(px(g), T + rh * len(rows) + 20, g, 10.5, C.MUT, "middle"))
    out.append(text(L + pw / 2, H - 8, "Months to cover the acquisition fee", 11,
                    C.MUT, "middle"))
    for i, (band, mth, roi) in enumerate(rows):
        y = T + rh * i + rh * 0.24
        out.append(text(L - 12, y + rh * 0.38, band, 12.5, C.NAVY, "end", True))
        if mth is None or mth > months:
            out.append(text(L + 6, y + rh * 0.38,
                            "never covers the fee within ten years", 11.5, C.MUT))
            continue
        out.append(rect(L, y, max(px(mth) - L, 1), rh * 0.5,
                        C.BAND_COLOUR.get(band, C.MUT), 4))
        out.append(text(px(mth) + 10, y + rh * 0.38,
                        "%d months  ·  %.2fx return" % (round(mth), roi),
                        12, C.NAVY, bold=True))
    return svg(W, H, "".join(out))

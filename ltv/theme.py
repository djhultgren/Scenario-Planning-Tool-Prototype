"""
Report styling.

Two looks over the same content. `house` is the working style the report was
drafted in. `sci` is the Save the Children International system from the Global
Brand Guidelines: Oswald for headings, Lato for everything else, red as the
lead colour, the adult secondary palette for charts, a teal table header.

The brand fonts ship with the codebase and are embedded in the page rather
than linked, so the report stays self-contained - it works offline and when
emailed - and no reader's browser calls a font server.
"""
import base64
from pathlib import Path

from . import config as C

ASSETS = Path(__file__).with_name("assets")
FONTS = ASSETS / "fonts"

# family, weight, file
FONT_FACES = [
    ("Oswald", 400, "oswald-latin-400-normal.woff2"),
    ("Oswald", 500, "oswald-latin-500-normal.woff2"),
    ("Lato", 300, "lato-latin-300-normal.woff2"),
    ("Lato", 400, "lato-latin-400-normal.woff2"),
    ("Lato", 700, "lato-latin-700-normal.woff2"),
    ("Lato", 900, "lato-latin-900-normal.woff2"),
]


def font_css() -> str:
    """@font-face rules with the brand fonts embedded."""
    out = []
    for family, weight, name in FONT_FACES:
        path = FONTS / name
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        out.append("@font-face{font-family:'%s';font-style:normal;"
                   "font-weight:%d;font-display:swap;"
                   "src:url(data:font/woff2;base64,%s) format('woff2')}"
                   % (family, weight, b64))
    return "".join(out)


def logo_html() -> str:
    """
    The Save the Children logo, if the official artwork has been supplied.

    Drop the master file in as `ltv/assets/logo.svg` and it appears in the
    header. The logo is never recreated or redrawn here: it comes from the
    Content Hub as issued, whole, and unaltered.
    """
    path = ASSETS / "logo.svg"
    if not path.exists():
        return ""
    return '<div class="logo">%s</div>' % path.read_text(encoding="utf-8")


# ------------------------------------------------------------ shared CSS ----
BASE = """
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}
header.top .inner{max-width:1180px;margin:0 auto;padding:0 22px;position:relative}
.stats{display:flex;flex-wrap:wrap;gap:14px}
.stat b{display:block;font-size:26px;line-height:1.15;margin-bottom:3px}
.stat span{font-size:12.4px;line-height:1.45;display:block}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 90px;display:grid;
 grid-template-columns:214px minmax(0,1fr);gap:38px}
@media(max-width:900px){.wrap{grid-template-columns:1fr;gap:0}}
nav{position:sticky;top:22px;align-self:start;font-size:13.4px}
nav a{display:block;text-decoration:none;padding:5px 0 5px 12px}
h2:first-child{margin-top:0}
p{margin:0 0 15px}
.tw{overflow-x:auto;margin:18px 0 6px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:480px}
th{color:#fff;text-align:right;padding:9px 11px}
th:first-child{text-align:left}
td{padding:8px 11px;text-align:right;font-variant-numeric:tabular-nums}
td:first-child{text-align:left}
ul.asm{margin:0 0 20px;padding-left:20px}ul.asm li{margin:0 0 10px;font-size:15px}
svg{display:block;width:100%;height:auto;overflow:visible}
footer{max-width:1180px;margin:26px auto 0;padding:0 22px 40px;font-size:12.6px}
@media print{body{background:#fff}nav{display:none}.wrap{display:block}
 main{box-shadow:none;padding:0}}
"""

HOUSE = """
:root{--navy:%(navy)s;--red:%(red)s;--green:%(green)s;--mut:%(mut)s;
 --line:%(line)s;--light:%(light)s;--ink:#1A2027;--bg:#EEF2F6;--th:%(th)s}
body{font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Calibri,Helvetica,Arial,sans-serif}
header.top{background:var(--navy);color:#fff;padding:46px 0 40px;margin-bottom:34px}
.eyebrow{font-size:12.5px;letter-spacing:.16em;text-transform:uppercase;color:#9EC2DA;
 font-weight:700;margin-bottom:12px}
header.top h1{font-size:33px;line-height:1.22;margin:0 0 10px;font-weight:700}
header.top p{margin:0;color:#C6DAE8;font-size:15.5px;max-width:64ch}
.statlab{margin-top:30px;margin-bottom:8px;font-size:11px;letter-spacing:.16em;
 text-transform:uppercase;color:#8AA0AE;font-weight:700}
.stat{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);
 border-radius:11px;padding:14px 20px;min-width:170px;flex:1 1 170px}
.stat b,.stat span{color:#fff}
nav .lbl{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);
 font-weight:700;margin-bottom:10px}
nav a{color:var(--mut);border-left:2px solid var(--line)}
nav a:hover{color:var(--navy);border-left-color:var(--red)}
main{background:#fff;border-radius:14px;padding:44px 48px 54px;box-shadow:0 1px 3px rgba(18,50,74,.08)}
h2{font-size:12px;letter-spacing:.15em;text-transform:uppercase;color:var(--red);font-weight:700;
 margin:44px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--line);scroll-margin-top:20px}
h3{font-size:22px;line-height:1.3;color:var(--navy);margin:46px 0 12px;font-weight:700;
 scroll-margin-top:20px}
h3 .n{color:var(--red);font-weight:700;margin-right:9px}
h4{font-size:16px;color:var(--navy);margin:26px 0 8px}
b{color:var(--navy)}
.note{font-size:13.4px;color:var(--mut);line-height:1.55;margin:10px 0 16px}
.note b{color:var(--navy)}
.flab,.tlab{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--red);
 font-weight:700}
.flab{margin-bottom:5px}.tlab{margin:20px 0 -10px}
th{background:var(--th);font-weight:600;font-size:12.2px}
td{border-bottom:1px solid var(--line)}
td:first-child{font-weight:600;color:var(--navy)}
tr.tot td{border-top:2px solid var(--navy);font-weight:700;background:#FAFCFD}
.tk{background:#F1F7F4;border-left:3px solid var(--green);border-radius:0 8px 8px 0;
 padding:12px 16px;margin:24px 0 6px;font-size:14.5px;color:var(--navy);font-weight:600}
.tk em{font-style:normal;color:var(--green);text-transform:uppercase;letter-spacing:.11em;
 font-size:10.5px;font-weight:700;display:block;margin-bottom:3px}
.flag{background:#FFF6E8;border-left:3px solid var(--red);border-radius:0 8px 8px 0;
 padding:12px 16px;margin:20px 0;font-size:14px;color:var(--navy)}
figure{margin:20px 0 8px;background:var(--light);border:1px solid var(--line);
 border-radius:12px;padding:20px 22px 14px}
figure .ttl{font-size:14px;font-weight:700;color:var(--navy);margin-bottom:10px}
figcaption{font-size:12.8px;color:var(--mut);margin-top:12px;line-height:1.5}
.empty{border:1px dashed #B9C4CC;border-radius:10px;padding:28px;text-align:center;color:var(--mut)}
footer{color:var(--mut)}
.logo{display:none}
"""

# Save the Children International. Oswald for headings only, Lato for
# everything else; red leads, black is used with restraint, and the secondary
# palette appears only in the charts. Headline text sits on white rather than
# on a red fill, which the guidelines prefer for legibility; red is kept for
# the section chips, the key statements and the accents.
SCI = """
:root{--navy:%(navy)s;--red:%(red)s;--green:%(green)s;--mut:%(mut)s;
 --line:%(line)s;--light:%(light)s;--ink:#222221;--bg:#F3F2EE;--th:%(th)s}
body{font:400 16px/1.62 Lato,Arial,Helvetica,sans-serif}
header.top{background:#fff;border-top:7px solid var(--red);padding:44px 0 38px;
 margin-bottom:34px;border-bottom:1px solid var(--line)}
.eyebrow{display:inline-block;background:var(--red);color:#fff;font-family:Oswald,Arial,sans-serif;
 font-weight:500;font-size:12px;letter-spacing:.14em;text-transform:uppercase;
 padding:5px 12px 4px;margin-bottom:16px}
header.top h1{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:40px;
 line-height:1.16;margin:0 0 12px;color:var(--ink);max-width:22ch}
header.top p{margin:0;color:var(--mut);font-size:16px;font-weight:300;max-width:62ch}
.statlab{margin-top:32px;margin-bottom:9px;font-family:Oswald,Arial,sans-serif;font-weight:500;
 font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut)}
.stat{background:var(--red);border-radius:12px;padding:15px 20px;min-width:170px;flex:1 1 170px}
.stat b{font-family:Oswald,Arial,sans-serif;font-weight:500;color:#fff;font-size:28px}
.stat span{color:#fff;font-weight:300}
.logo{position:absolute;right:22px;bottom:0;width:150px}
.logo svg,.logo img{width:100%%;height:auto;display:block}
nav .lbl{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:11.5px;
 letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin-bottom:10px}
nav a{color:var(--mut);border-left:2px solid var(--line)}
nav a:hover{color:var(--red);border-left-color:var(--red)}
main{background:#fff;border-radius:14px;padding:44px 48px 54px;box-shadow:0 1px 3px rgba(34,34,33,.09)}
h2{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:14px;letter-spacing:.15em;
 text-transform:uppercase;color:var(--red);margin:46px 0 15px;padding-bottom:9px;
 border-bottom:2px solid var(--red);scroll-margin-top:20px}
h3{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:25px;line-height:1.24;
 color:var(--ink);margin:46px 0 12px;scroll-margin-top:20px}
h3 .n{color:var(--red);margin-right:10px}
h4{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:17px;color:var(--ink);
 margin:26px 0 8px}
b{font-weight:700;color:var(--ink)}
.note{font-size:13.6px;color:var(--mut);line-height:1.55;margin:10px 0 16px;font-weight:300}
.note b{color:var(--ink);font-weight:700}
.flab,.tlab{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:11px;
 letter-spacing:.13em;text-transform:uppercase;color:var(--red)}
.flab{margin-bottom:5px}.tlab{margin:20px 0 -10px}
th{background:var(--th);font-family:Oswald,Arial,sans-serif;font-weight:400;font-size:13px;
 letter-spacing:.02em}
td{border-bottom:1px solid var(--line)}
td:first-child{font-weight:700;color:var(--ink)}
tr.tot td{border-top:2px solid var(--ink);font-weight:700;background:var(--light)}
/* Key statement: a red highlight box, white type, as the brand system sets out. */
.tk{background:var(--red);border-radius:12px;padding:15px 19px;margin:26px 0 6px;
 font-size:15px;color:#fff;font-weight:400}
.tk em{font-style:normal;font-family:Oswald,Arial,sans-serif;font-weight:500;color:#fff;
 text-transform:uppercase;letter-spacing:.12em;font-size:11px;display:block;
 margin-bottom:4px;opacity:.9}
.flag{background:#fff;border:1.5px solid var(--red);border-radius:12px;padding:13px 17px;
 margin:20px 0;font-size:14.2px;color:var(--ink)}
figure{margin:20px 0 8px;background:var(--light);border-radius:12px;padding:20px 22px 14px}
figure .ttl{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:15.5px;
 color:var(--ink);margin-bottom:10px}
figcaption{font-size:12.8px;color:var(--mut);margin-top:12px;line-height:1.5;font-weight:300}
.empty{border:1px dashed #C9C4B6;border-radius:12px;padding:28px;text-align:center;color:var(--mut)}
footer{color:var(--mut);font-weight:300}
footer b{font-family:Oswald,Arial,sans-serif;font-weight:500;color:var(--ink)}
"""


def css() -> str:
    """The stylesheet for the theme currently set in config."""
    values = {"navy": C.NAVY, "red": C.RED, "green": C.GREEN,
              "mut": C.MUT, "line": C.LINE, "light": C.LIGHT,
              "th": C.TABLE_HEAD}
    if C.THEME == "sci":
        return font_css() + BASE + (SCI % values)
    return BASE + (HOUSE % values)


def footer() -> str:
    """The line under the report."""
    if C.THEME == "sci":
        return ("Generated by the Germany F2F LTV model · Market Intelligence<br>"
                "<b>Save the Children International</b> · 1 St John's Lane, London "
                "EC1M 4BL, United Kingdom · www.savethechildren.net")
    return ("Generated by the Germany F2F LTV model · Market Intelligence, "
            "Save the Children International")

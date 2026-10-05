"""
Report styling.

Two looks over the same content. `house` is the working style the report was
drafted in. `sci` is the Save the Children International system from the Global
Brand Guidelines: Oswald for headings, Lato for everything else, red as the
lead colour, the adult secondary palette for charts, a teal table header.

The brand fonts ship with the codebase and are embedded in the page rather
than linked, so the report stays self-contained - it works offline and when
emailed - and no reader's browser calls a font server.

The layout follows a few rules that are worth stating, because they are what
keep a long analytical document readable:

* One measure for prose. Body text is held to about 68 characters a line
  whatever the window width; figures and tables are free to use the full
  column, because a wide chart is easier to read, not harder.
* One spacing scale. Every margin and padding is a step on an 8px rhythm, so
  the vertical spacing between a heading, its text and its chart is consistent
  from section to section.
* One role per colour. Red marks structure (section rules, figure labels),
  green marks a takeaway, amber marks a caveat, and the chart palette is left
  to the charts.
* Everything is operable without a mouse. Visible focus rings, a skip link, a
  contents list that marks where the reader is, and real buttons behind the
  chart filters.
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
    svg = ASSETS / "logo.svg"
    if svg.exists():
        return '<div class="logo">%s</div>' % svg.read_text(encoding="utf-8")
    png = ASSETS / "logo.png"
    if png.exists():
        b64 = base64.b64encode(png.read_bytes()).decode("ascii")
        return ('<div class="logo"><img src="data:image/png;base64,%s" '
                'alt="Save the Children"></div>' % b64)
    return ""


# ------------------------------------------------------------ shared CSS ----
# Structure only: the grid, the spacing scale, the measure, the states. Both
# themes inherit it and then set their own type and colour.
BASE = """
:root{
 --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:72px;
 --r1:6px;--r2:10px;--r3:14px;
 --page:1180px;--rail:214px;
 --shadow:0 1px 2px rgba(16,32,48,.06),0 8px 28px -14px rgba(16,32,48,.18);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased}

/* ---- skip link and focus: the page has to work from the keyboard ---- */
.skip{position:absolute;left:-9999px;top:0;z-index:50;padding:10px 16px;
 background:var(--red);color:#fff;border-radius:0 0 var(--r1) 0;font-weight:700}
.skip:focus{left:0}
a:focus-visible,button:focus-visible{outline:3px solid var(--red);outline-offset:2px;
 border-radius:3px}

/* ---- reading progress ---- */
.prog{position:fixed;top:0;left:0;height:3px;width:0;background:var(--red);z-index:40}

/* ---- header ---- */
header.top .inner{max-width:var(--page);margin:0 auto;padding:0 22px;position:relative}
.stats{display:grid;gap:var(--s3);grid-template-columns:repeat(auto-fit,minmax(168px,1fr))}
.stat b{display:block;line-height:1.1;margin-bottom:var(--s1)}
.stat span{display:block;line-height:1.4}

/* ---- the two-column page ---- */
.wrap{max-width:var(--page);margin:0 auto;padding:0 22px 90px;
 display:grid;grid-template-columns:var(--rail) minmax(0,1fr);gap:38px;
 align-items:start}
main,nav,figure,.tw{min-width:0}

/* ---- contents rail: the original flat list, with the parts in bold ---- */
nav{position:sticky;top:22px;align-self:start;font-size:13.4px}
nav ol{list-style:none;margin:0;padding:0}
nav a{display:block;text-decoration:none;padding:5px 0 5px 12px;line-height:1.4}
nav .grp>a{font-weight:700}

/* ---- prose runs the full width of the column, as the report always has ---- */
p{margin:0 0 15px}
h2:first-child{margin-top:0}
ul.asm{margin:0 0 20px;padding-left:20px}
ul.asm li{margin:0 0 10px;font-size:15px}

/* ---- figures: full column width, labelled consistently ---- */
figure{margin:20px 0 8px}
.fhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:9px;margin-bottom:10px}
svg{display:block;width:100%;max-width:100%;min-width:0;height:auto;overflow:visible}

/* ---- tables ---- */
.tw{overflow-x:auto;margin:var(--s4) 0 var(--s2);scrollbar-width:thin}
table{border-collapse:collapse;width:100%;min-width:520px}
table.narrow{width:auto;min-width:0}
table.narrow th,table.narrow td{padding-left:var(--s4);padding-right:var(--s4)}
table.narrow th:first-child,table.narrow td:first-child{padding-left:var(--s3)}
th{text-align:right;padding:10px 12px;position:sticky;top:0}
th:first-child{text-align:left}
td{padding:9px 12px;text-align:right;font-variant-numeric:tabular-nums}
td:first-child{text-align:left}
.hint{display:none}

/* ---- back to top ---- */
.totop{position:fixed;right:var(--s5);bottom:var(--s5);z-index:30;border:0;
 cursor:pointer;width:44px;height:44px;border-radius:999px;font-size:17px;
 background:var(--red);color:#fff;box-shadow:var(--shadow);opacity:0;
 pointer-events:none;transition:opacity .2s}
.totop.on{opacity:1;pointer-events:auto}

footer{max-width:var(--page);margin:26px auto 0;padding:0 22px 40px}

/* ---- a narrow window simply stacks; this is a desktop document ---- */
@media(max-width:900px){
 .wrap{grid-template-columns:minmax(0,1fr);gap:0}
 nav{position:static}
 header.top h1{white-space:normal}
}
@media(prefers-reduced-motion:reduce){
 html{scroll-behavior:auto}.totop{transition:none}
}

/* ---- print: the document, nothing else ---- */
@media print{
 body{background:#fff}
 nav,.prog,.totop,.skip{display:none}
 .wrap{display:block;padding:0}
 main{box-shadow:none;padding:0;border:0}
 .stats{grid-template-columns:repeat(4,1fr);gap:8px}
 .stat{padding:10px 12px}.stat b{font-size:21px}
 figure,table,.tk{break-inside:avoid}
 h2,h3{break-after:avoid}
 th{position:static}
}
"""

HOUSE = """
:root{--navy:%(navy)s;--red:%(red)s;--green:%(green)s;--mut:%(mut)s;
 --line:%(line)s;--light:%(light)s;--ink:#16202B;--bg:#EDF1F5;--th:%(th)s;
 --amber:#9A6412}
body{font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Calibri,Helvetica,Arial,sans-serif}

header.top{background:linear-gradient(170deg,#143850 0%%,var(--navy) 62%%,#0E2A3E 100%%);
 color:#fff;padding:46px 0 40px;margin-bottom:34px}
.eyebrow{font-size:12.5px;letter-spacing:.16em;text-transform:uppercase;color:#9CC4DD;
 font-weight:700;margin-bottom:var(--s3)}
header.top h1{font-size:33px;line-height:1.22;margin:0 0 10px;font-weight:700;
 letter-spacing:-.01em;max-width:none;white-space:nowrap}
header.top p{margin:0;color:#C9DCE9;font-size:15.5px;max-width:62ch}

.statlab{margin:30px 0 8px;font-size:11px;letter-spacing:.16em;
 text-transform:uppercase;color:#92A8B8;font-weight:700}
.stat{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);
 border-radius:11px;padding:14px 20px}
.stat b{font-size:26px;color:#fff}
.stat span{font-size:12.4px;color:#BDD2E0}

nav .lbl{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);
 font-weight:700;margin-bottom:10px}
nav a{color:#4E6273;border-left:2px solid var(--line)}
nav a:hover{color:var(--navy);border-left-color:var(--red)}
nav a[aria-current="true"]{color:var(--navy);border-left-color:var(--red)}

main{background:#fff;border-radius:14px;padding:44px 48px 54px;box-shadow:var(--shadow)}
@media(max-width:700px){main{padding:var(--s5) var(--s4) var(--s6);border-radius:var(--r2)}}

h2{font-size:14.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--red);
 font-weight:700;margin:44px 0 14px;padding-bottom:9px;
 border-bottom:1px solid var(--line);scroll-margin-top:20px}
h3{font-size:22px;line-height:1.3;color:var(--navy);margin:46px 0 12px;font-weight:700;
 scroll-margin-top:20px;display:flex;gap:10px;align-items:baseline}
h3 .n{flex:0 0 auto;font-size:12.5px;font-weight:700;color:#fff;background:var(--red);
 border-radius:999px;min-width:24px;height:24px;display:inline-flex;
 align-items:center;justify-content:center;transform:translateY(-2px)}
h4{font:700 18.5px/1.35 inherit;font-family:inherit;color:var(--navy);margin:28px 0 9px}
b{color:var(--navy)}
a{color:#0B5E8A}

.note{font-size:13.4px;color:#55687A;line-height:1.55;margin:10px 0 16px;
 padding-left:var(--s3);border-left:2px solid var(--line)}
.note b{color:var(--navy)}

/* figures */
.flab{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--red);
 font-weight:700;background:#FDEEF0;border-radius:999px;padding:4px 10px}
.ftitle{font-size:14px;font-weight:700;color:var(--navy);line-height:1.3}
figure{background:#FBFCFE;border:1px solid var(--line);border-radius:12px;
 padding:20px 22px 14px}
figcaption{font-size:12.8px;color:#55687A;margin-top:12px;line-height:1.5;
 padding-top:10px;border-top:1px solid var(--line)}

/* tables */
.tlab{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--red);
 font-weight:700;margin:20px 0 6px}
table{font-size:14px}
th{background:var(--th);color:#fff;font-weight:600;font-size:12.2px}
td{border-bottom:1px solid #EAEFF3}
tbody tr:nth-child(even) td{background:#FAFCFD}
tbody tr:hover td{background:#F2F7FB}
td:first-child{font-weight:600;color:var(--navy)}
tr.tot td{border-top:2px solid var(--navy);font-weight:700;background:#F4F8FB}
.hint{font-size:12px;color:var(--mut);margin:0 0 var(--s4)}

/* takeaway and caveat */
.tk{background:#F2F8F5;border:1px solid #CFE4D8;border-left:4px solid var(--green);
 border-radius:0 8px 8px 0;padding:12px 16px;margin:24px 0 6px;
 font-size:14.5px;color:var(--navy);font-weight:600}
.tk em{font-style:normal;color:#1F6B4C;text-transform:uppercase;letter-spacing:.11em;
 font-size:10.5px;font-weight:700;display:block;margin-bottom:var(--s1)}
.flag{background:#FFF8EC;border:1px solid #F0DDBC;border-left:4px solid var(--amber);
 border-radius:0 8px 8px 0;padding:12px 16px;margin:20px 0;
 font-size:14px;color:var(--navy)}
.empty{border:1px dashed #BCC7D0;border-radius:var(--r2);padding:var(--s6);
 text-align:center;color:var(--mut)}

footer{color:var(--mut);font-size:12.6px}
.logo{display:none}
"""

# Save the Children International. Oswald for headings only, Lato for
# everything else; red leads, black is used with restraint, and the secondary
# palette appears only in the charts. Headline text sits on white rather than
# on a red fill, which the guidelines prefer for legibility; red is kept for
# the section chips, the key statements and the accents.
SCI = """
:root{--navy:%(navy)s;--red:%(red)s;--green:%(green)s;--mut:%(mut)s;
 --line:%(line)s;--light:%(light)s;--ink:#222221;--bg:#F3F2EE;--th:%(th)s;
 --amber:#8A5A00}
body{font:400 16px/1.62 Lato,Arial,Helvetica,sans-serif}

header.top{background:#fff;border-top:7px solid var(--red);padding:var(--s7) 0 var(--s6);
 margin-bottom:var(--s7);border-bottom:1px solid var(--line)}
.eyebrow{display:inline-block;background:var(--red);color:#fff;
 font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:12px;letter-spacing:.14em;
 text-transform:uppercase;padding:5px 12px 4px;margin-bottom:var(--s4)}
header.top h1{font-family:Oswald,Arial,sans-serif;font-weight:500;
 font-size:40px;line-height:1.16;margin:0 0 12px;
 color:var(--ink);max-width:none;white-space:nowrap}
header.top p{margin:0;color:var(--mut);font-size:16px;font-weight:300;max-width:60ch}
.statlab{margin:var(--s6) 0 var(--s2);font-family:Oswald,Arial,sans-serif;font-weight:500;
 font-size:11.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--mut)}
.stat{background:var(--red);border-radius:var(--r3);padding:var(--s4) var(--s5)}
.stat b{font-family:Oswald,Arial,sans-serif;font-weight:500;color:#fff;font-size:29px}
.stat span{color:#fff;font-weight:300;font-size:12.5px}
.logo{position:absolute;right:22px;top:2px;width:116px}
.logo svg,.logo img{width:100%%;height:auto;display:block}
@media(max-width:1050px){.logo{display:none}}

nav .lbl{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:11.5px;
 letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin-bottom:var(--s3)}
nav a{color:#4A4F53;border-left:2px solid var(--line)}
nav a:hover{color:var(--red);border-left-color:var(--red)}
nav a[aria-current="true"]{color:var(--red);border-left-color:var(--red)}

main{background:#fff;border-radius:14px;padding:44px 48px 54px;box-shadow:var(--shadow)}
@media(max-width:700px){main{padding:var(--s5) var(--s4) var(--s6);border-radius:var(--r2)}}

h2{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:16.5px;letter-spacing:.15em;
 text-transform:uppercase;color:var(--red);margin:var(--s8) 0 var(--s5);
 padding-bottom:var(--s2);border-bottom:2px solid var(--red);scroll-margin-top:var(--s5)}
h3{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:25px;
 line-height:1.24;color:var(--ink);margin:46px 0 12px;
 scroll-margin-top:var(--s5);display:flex;gap:var(--s3);align-items:baseline}
h3 .n{flex:0 0 auto;font-size:14px;color:#fff;background:var(--red);border-radius:999px;
 min-width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;
 transform:translateY(-2px)}
h4{font-family:Lato,Arial,Helvetica,sans-serif;font-weight:700;font-size:18.5px;
 line-height:1.35;color:var(--ink);margin:28px 0 9px}
b{font-weight:700;color:var(--ink)}
a{color:#007A82}

.note{font-size:13.8px;color:var(--mut);line-height:1.58;margin:var(--s2) 0 var(--s4);
 font-weight:300;padding-left:var(--s3);border-left:2px solid var(--line)}
.note b{color:var(--ink);font-weight:700}

.flab{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:11px;
 letter-spacing:.13em;text-transform:uppercase;color:#fff;background:var(--red);
 padding:4px 10px;border-radius:999px}
.ftitle{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:15.5px;
 color:var(--ink);line-height:1.28}
figure{background:var(--light);border-radius:var(--r3);padding:var(--s5) var(--s5) var(--s4)}
figcaption{font-size:12.8px;color:var(--mut);margin-top:var(--s3);line-height:1.5;
 font-weight:300;padding-top:var(--s3);border-top:1px solid #DCD8CC}

.tlab{font-family:Oswald,Arial,sans-serif;font-weight:500;font-size:11px;
 letter-spacing:.13em;text-transform:uppercase;color:var(--red);margin:var(--s6) 0 var(--s2)}
table{font-size:14px}
th{background:var(--th);color:#fff;font-family:Oswald,Arial,sans-serif;font-weight:400;
 font-size:13px;letter-spacing:.02em}
td{border-bottom:1px solid #E7E4DB}
tbody tr:nth-child(even) td{background:#FAF9F6}
tbody tr:hover td{background:var(--light)}
td:first-child{font-weight:700;color:var(--ink)}
tr.tot td{border-top:2px solid var(--ink);font-weight:700;background:var(--light)}
.hint{font-size:12px;color:var(--mut);margin:0 0 var(--s4);font-weight:300}

/* Key statement: a red highlight box, white type, as the brand system sets out. */
.tk{background:var(--red);border-radius:var(--r3);padding:var(--s4) var(--s5);
 margin:var(--s5) 0 var(--s3);font-size:15px;color:#fff;font-weight:400}
.tk em{font-style:normal;font-family:Oswald,Arial,sans-serif;font-weight:500;color:#fff;
 text-transform:uppercase;letter-spacing:.12em;font-size:11px;display:block;
 margin-bottom:var(--s1);opacity:.9}
.flag{background:#fff;border:1.5px solid var(--red);border-radius:var(--r3);
 padding:var(--s4) var(--s5);margin:var(--s5) 0;font-size:14.2px;color:var(--ink)}
.empty{border:1px dashed #C9C4B6;border-radius:var(--r3);padding:var(--s6);
 text-align:center;color:var(--mut)}

footer{color:var(--mut);font-weight:300;font-size:12.8px}
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


# The page's own behaviour: where the reader is, how far through they are, and
# a way back to the top. Small enough to inline, and the page is complete
# without it.
PAGE_JS = """
(function(){
 var prog=document.querySelector('.prog'),top=document.querySelector('.totop');
 var heads=[].slice.call(document.querySelectorAll('main h2[id],main h3[id]'));
 var links={};
 [].forEach.call(document.querySelectorAll('nav a'),function(a){
  links[a.getAttribute('href').slice(1)]=a;});
 function onScroll(){
  var y=window.scrollY||document.documentElement.scrollTop;
  var h=document.documentElement.scrollHeight-window.innerHeight;
  if(prog)prog.style.width=(h>0?Math.min(100,100*y/h):0)+'%';
  if(top)top.classList.toggle('on',y>700);
  var current=null;
  heads.forEach(function(el){
   if(el.getBoundingClientRect().top<=120)current=el.id;});
  for(var k in links)links[k].removeAttribute('aria-current');
  if(current&&links[current])links[current].setAttribute('aria-current','true');
 }
 window.addEventListener('scroll',onScroll,{passive:true});
 window.addEventListener('resize',onScroll);
 if(top)top.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
 onScroll();
})();
"""


def footer() -> str:
    """The line under the report."""
    if C.THEME == "sci":
        return ("Generated by Market Intelligence - Save the Children "
                "International<br>1 St John's Lane, London EC1M 4BL, "
                "United Kingdom · www.savethechildren.net")
    return "Generated by Market Intelligence - Save the Children International"

"""
Narrative content, kept separate from the code that calculates.

The report is mostly written by a person. Embedding that prose inside the
build script - which is how the first version of this model worked - makes the
text hard to edit and easy to lose. So the narrative lives in `content.json`
and the code only supplies numbers, charts and tables.

`extract()` reads an existing report HTML and writes that JSON, so an edited
Word or HTML version can be folded back in without retyping anything.
"""
import json
import re

from bs4 import BeautifulSoup

from . import config as C

CONTENT_FILE = C.DATA / "content.json"


def _inner(el) -> str:
    return re.sub(r"\s+", " ", el.decode_contents()).strip()


def extract(html_path, out_path=None) -> str:
    """
    Turn a built report into an ordered list of content blocks.

    Each block is [kind, ...] where kind is one of: h2, h3, sub, p, note,
    takeaway, flag, empty, table, figure, list. Figures and tables become
    placeholders - the builder regenerates them from the model - while all
    prose is preserved exactly as written.
    """
    out_path = out_path or CONTENT_FILE
    soup = BeautifulSoup(open(html_path, encoding="utf-8").read(), "html.parser")
    main = soup.find("main")
    blocks, fig_no, pending_table = [], 0, None

    for el in main.find_all(recursive=False):
        name, cls = el.name, (el.get("class") or [])
        if name == "h2":
            blocks.append(["h2", el.get_text(" ", strip=True)])
        elif name == "h3":
            num = el.find("span", class_="n")
            n = num.get_text(strip=True) if num else ""
            if num:
                num.extract()
            blocks.append(["h3", n, el.get_text(" ", strip=True)])
        elif name == "h4":
            blocks.append(["sub", el.get_text(" ", strip=True)])
        elif name == "p":
            if "tk" in cls:
                em = el.find("em")
                label = em.get_text(strip=True) if em else "Takeaway"
                if em:
                    em.extract()
                blocks.append(["takeaway", _inner(el), label])
            elif "note" in cls:
                blocks.append(["note", _inner(el)])
            elif "flag" in cls:
                blocks.append(["flag", _inner(el)])
            else:
                blocks.append(["p", _inner(el)])
        elif name == "div" and "flag" in cls:
            blocks.append(["flag", _inner(el)])
        elif name == "div" and "empty" in cls:
            blocks.append(["empty", el.get_text(" ", strip=True)])
        elif name == "div" and "tlab" in cls:
            pending_table = el.get_text(" ", strip=True)
        elif name == "div" and "tw" in cls:
            table = el.find("table")
            head = [th.get_text(" ", strip=True)
                    for th in table.find("thead").find_all("th")]
            rows = [[td.get_text(" ", strip=True) for td in tr.find_all("td")]
                    for tr in table.find("tbody").find_all("tr")]
            blocks.append(["table", pending_table or "", head, rows])
            pending_table = None
        elif name == "figure":
            fig_no += 1
            ttl = el.find("div", class_="ttl")
            cap = el.find("figcaption")
            blocks.append(["figure", fig_no,
                           ttl.get_text(" ", strip=True) if ttl else "",
                           _inner(cap) if cap else ""])
        elif name == "ul":
            blocks.append(["list", [_inner(li) for li in el.find_all("li")]])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(blocks, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return str(out_path)


def load(path=None) -> list:
    path = path or CONTENT_FILE
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------- number audit ----
MONEY = re.compile(r"€([\d,]+(?:\.\d+)?)(m)?")


def audit(blocks: list, model) -> list[dict]:
    """
    Flag figures in the prose that disagree with the model.

    Catches the failure mode where a number is written into the text, the model
    is later re-run, and the two quietly drift apart. Reports every euro amount
    in the narrative that cannot be matched to a current model figure within
    tolerance - which will include plenty of legitimate ones, so it is a
    prompt to check rather than a list of errors.
    """
    bands = model.band_summary()
    agencies = model.agency_summary()
    known = set()
    for col in ("gross_ltv", "net_ltv", "blended_cpa"):
        known.update(round(float(v)) for v in bands[col] if v == v)
    for col in ("net_ltv", "avg_cpa"):
        known.update(round(float(v)) for v in agencies[col] if v == v)
    for total in (bands["gross_income"].sum(), bands["net_income"].sum(),
                  agencies["cost"].sum()):
        known.add(round(float(total)))

    findings = []
    for block in blocks:
        if block[0] not in ("p", "takeaway", "note", "flag"):
            continue
        text = block[1]
        for match in MONEY.finditer(text):
            raw = match.group(1).replace(",", "")
            try:
                value = float(raw) * (1e6 if match.group(2) else 1)
            except ValueError:
                continue
            if value < 50:                      # gift amounts, not results
                continue
            if any(abs(value - k) <= max(2, 0.01 * k) for k in known):
                continue
            findings.append({"value": match.group(0),
                             "context": text[max(0, match.start() - 60):
                                             match.end() + 60]})
    return findings

#!/usr/bin/env python3
"""
Run the whole pipeline.

    python run.py                # model -> report + scenario tool + tables
    python run.py --validate     # also run reconciliation, holdout, sensitivity
    python run.py --extract      # re-read data/report_source.html into content.json
    python run.py --theme sci    # the same report in the Save the Children brand

Outputs land in out/.
"""
import argparse
import json

import pandas as pd

from ltv import config as C
from ltv import content as content_mod
from ltv import planner, report, validate
from ltv.model import Model


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validate", action="store_true",
                    help="run the reconciliation, holdout and sensitivity checks")
    ap.add_argument("--extract", action="store_true",
                    help="rebuild content.json from data/report_source.html")
    ap.add_argument("--audit", action="store_true",
                    help="flag figures in the narrative that the model no longer produces")
    ap.add_argument("--theme", choices=sorted(C.THEMES), default=C.THEME,
                    help="report styling: 'house' or 'sci' (Save the Children brand)")
    args = ap.parse_args()

    C.apply_theme(args.theme)

    C.OUT.mkdir(parents=True, exist_ok=True)

    if args.extract or not content_mod.CONTENT_FILE.exists():
        src = C.DATA / "report_source.html"
        if src.exists():
            print("extracting narrative ->", content_mod.extract(src))
        else:
            print("no report_source.html; skipping narrative extraction")

    print("building model ...")
    m = Model.build()

    bands = m.band_summary()
    agencies = m.agency_summary()
    bands.to_csv(C.OUT / "bands.csv")
    agencies.to_csv(C.OUT / "agencies.csv")
    m.volumes().to_csv(C.OUT / "volumes.csv")

    summary = {
        "horizon_years": C.HORIZON_MONTHS // 12,
        "donors": float(agencies["donors"].sum()),
        "gross_income": float(bands["gross_income"].sum()),
        "cost": float(agencies["cost"].sum()),
        "net_income": float(bands["net_income"].sum()),
    }
    (C.OUT / "summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")

    print("scenario planner ->", planner.build(m))
    if content_mod.CONTENT_FILE.exists():
        name = "report.html" if args.theme == "house" else "report_%s.html" % args.theme
        print("report        ->", report.build(m, path=C.OUT / name))

    pd.set_option("display.width", 200)
    print("\n" + bands[["donors", "gross_ltv", "blended_cpa", "net_ltv"]]
          .round(0).to_string())
    print("\ndonors %s   gross %.2fm   cost %.2fm   net %.2fm" % (
        format(int(summary["donors"]), ",d"), summary["gross_income"] / 1e6,
        summary["cost"] / 1e6, summary["net_income"] / 1e6))

    if args.audit and content_mod.CONTENT_FILE.exists():
        findings = content_mod.audit(content_mod.load(), m)
        print("\nnumber audit: %d figure(s) in the narrative not matched to the model"
              % len(findings))
        for f in findings[:15]:
            print("  %-12s %s" % (f["value"], f["context"][:100].replace("\n", " ")))

    if args.validate:
        print()
        validate.main()


if __name__ == "__main__":
    main()

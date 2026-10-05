# Germany F2F LTV model - handover

Everything needed to rebuild the report is in this archive. Unzip it, upload it at
the start of a new chat, and the current version can be rebuilt in one command.

## Rebuild

    pip install -r requirements.txt
    python run.py                 # out/report.html  (plain)
    python run.py --theme sci     # out/report_sci.html  (Save the Children brand)
    python run.py --word          # also writes out/report.docx
    python run.py --validate      # reconciliation, holdout and sensitivity checks

The current delivered version is **v37**.

## What is where

    data/historic_donors.xlsx   donor behaviour: retention flags, first-year value, upgrades
    data/cohort_2026.xlsx       who we are acquiring now, one row per pledge
    data/agency_costs.xlsx      agency spend, realised donors, fee factors
    data/content.json           the narrative - every word of the report
    data/next_version_log.md    open items, what was actioned, and the standing rules
    data/report_source.html     the original v27 report, kept for reconciliation

    ltv/config.py       every judgement call: bands, horizons, fee caps, thresholds, themes
    ltv/data.py         reads the three spreadsheets
    ltv/survival.py     retention curves and the sBG projection beyond year five
    ltv/model.py        the model itself - curves, LTV, volumes, agency economics
    ltv/figures.py      one function per figure
    ltv/charts.py       the SVG drawing, including the chart filters
    ltv/tables.py       the eight tables, generated from the model
    ltv/theme.py        the two looks, the page CSS, fonts and logo
    ltv/report.py       assembles the HTML
    ltv/planner.py      the standalone scenario planner
    ltv/word.py         the .docx build
    ltv/validate.py     the checks
    ltv/assets/         embedded Oswald and Lato, and the Save the Children logo

## Personal data

The cohort extract originally carried `SupporterID`, two pledge references and
exact pledge dates, and the historic extract carried date of birth. None of them
were used by the model. They have been removed from the files in `data/`, and
`ltv/data.py` now strips identifiers, dates of birth and exact dates from any
file as it is read, so a future extract that still contains them cannot carry
them into the model, an export or a copy of this repository.

What remains is individual-level but not identifying: age at acquisition, gift
amount, payment frequency, source code and retention flags. Treat it as
confidential supporter data all the same - it should not go into a public
repository, and a private one is worth clearing with whoever covers data
protection.

## Worth knowing

* The numbers are generated, never typed. Change the model and every figure,
  table and total in the report moves with it.
* `data/content.json` holds the words. Tables and figures in it are matched to
  the model's own by their header row, so a written table that no longer matches
  is left exactly as written rather than silently dropped.
* The logo is a cleaned copy of a third-party PNG. Replace it with the Content
  Hub master (CH1648971) as `ltv/assets/logo.svg` before anything external - the
  SVG is used in preference to the PNG automatically.
* Age means age at acquisition throughout, not age today.
* "Other" is a pooled catch-all: inside every headline total, out of every chart
  and table.

# Germany F2F — Donor Lifetime Value Model

Ten-year lifetime value model for face-to-face agency-acquired donors in
Germany. Produces the *Optimising Net Income and Net LTV* report, an
interactive scenario tool, and the underlying tables.

Built for the 2027 agency negotiations. Companion to the separate
**Methodology and Assumptions** document, which explains the reasoning behind
the choices made here in non-technical language.

---

## Quick start

```bash
pip install -r requirements.txt
python run.py                 # model → report, scenario tool, CSVs
python run.py --validate      # plus reconciliation, holdout, sensitivity
```

Outputs land in `out/`.

| Command | What it does |
|---|---|
| `python run.py` | Builds the model and writes all outputs |
| `python run.py --validate` | Adds the four validation checks (see below) |
| `python run.py --extract` | Re-reads `data/report_source.html` into `data/content.json` |
| `python run.py --audit` | Flags figures in the narrative the model no longer produces |
| `python run.py --theme sci` | The same report in the Save the Children brand |
| `python -m ltv.validate` | Validation only, without rebuilding outputs |

---

## What the model does

1. **Observe.** For each gift band × age band, measure retention at months 3,
   12, 24, 36, 48 and 60 from donors acquired 2019–2025. Age is age at
   acquisition, supplied in both extracts — not age today. Using age today
   would push the historic donors two to four years up the scale and make them
   incomparable with the 2026 cohort.
2. **Interpolate.** Join those anchor points on cumulative hazard, not in a
   straight line — retention decays geometrically, so linear interpolation
   would overstate the months in between.
3. **Project.** Extend to ten years with a shifted beta-geometric model
   (Fader & Hardie), fitted per age band. It assumes each donor has their own
   lapse probability drawn from a distribution, so the survivors become
   progressively more loyal and the curve flattens rather than continuing to
   fall at the year-one rate.
4. **Adjust for how donors pay.** A donor paying annually cannot lapse before
   their second gift falls due, so the retention flags record them as fully
   retained for a year whatever they go on to do. Annual and quarterly donors
   therefore use the observed retention schedules in
   `config.FREQUENCY_RETENTION` rather than that artefact; monthly and
   twice-yearly donors keep their own observed curve. Each band's curve is a
   blend, weighted by how its donors actually pay — which matters most for the
   €5 band, where 82% pay annually.
5. **Value.** Turn survival into income: effective monthly gift × months of
   giving, plus the upgrade uplift from month 13.
6. **Cost.** Subtract the acquisition fee — each donor at their own agency's
   rate, capped where a cap applies.

Two donor populations are used, deliberately kept apart:

- **Historic (2019–2025)** — tells us how donors *behave*. Never used for
  volumes or age profile.
- **2026 cohort** — tells us who we are *acquiring now*. Never used for
  behaviour; too recent to have retention.

---

## Layout

```
ltv/
  config.py     every judgement call — bands, horizons, thresholds, fee caps
  data.py       loading and preparing the three source files
  survival.py   retention curves and the sBG projection
  model.py      the model itself; everything else reads from here
  charts.py     SVG chart drawing
  figures.py    turns model output into the report's eleven figures
  report.py     assembles the HTML report
  planner.py    computes the scenario planner payload
  planner_template.html  the planner page
  content.py    narrative extraction and the number audit
  theme.py      report styling - the house look and the SCI brand
  validate.py   reconciliation, holdout, sensitivity, precision
  assets/fonts/ the brand fonts, embedded in the branded report
data/           source files (see schema below)
out/            generated outputs
run.py          pipeline entry point
```

### The scenario planner

`out/scenario_planner.html` lets someone build a 2026 acquisition plan, apply
optimisation levers to retention and upgrades, and compare saved scenarios
against the baseline.

The planner opens on the model. Volumes, survival curves, lifetime values and
fees are all read from `Model` rather than recomputed, so before any lever is
touched the page shows the report's own figures and reads *+€0 vs baseline*.
The levers move it from there: the retention slider scales the cumulative
hazard of the model's curve, and the lifetime value moves by the resulting
change in expected months of giving. Reconciliation against the report is
within €300 on €8.0m, which is donor counts being whole numbers.

Three things are set in Step 2 and flow through every figure on the page:

- **Agency** — price the plan on one agency's rate, or keep *All agencies* for
  a blend weighted by each agency's share of the 2026 cohort.
- **Fee cap on/off** — the cap applies to Trust and Activate. With it on, the
  gift is capped before the fee factor is applied, so a €30 donor costs the
  same as a €20 one. Switching it off shows what the same plan would cost
  without it.
- **Cap level** — the cap in euros per month.

The CPA table shows the arithmetic explicitly: fee factor × monthly gift = CPA,
with capped gifts marked. Each band carries the joint distribution of agency
and fee basis behind it, so repricing is exact rather than an average of
averages — which matters wherever the cap binds for some agencies and not
others.

Horizons are set by `PLANNER_HORIZONS` in `config.py`; the bands the planner
works in are `PLANNER_BANDS`, which are deliberately wider than the report's
point bands because a plan moves blocks of donors rather than setting exact
asks. Each planner band is the volume-weighted aggregate of the report bands
inside it.

### Branding

`python run.py --theme sci` writes `out/report_sci.html` - the same report,
same numbers, in the Save the Children International system: Oswald for
headings, Lato for everything else, red as the lead colour, a teal table
header, and the adult secondary palette in the charts. The default `house`
theme is untouched and still writes `out/report.html`.

The brand fonts are embedded in the page rather than linked, so the report
stays self-contained and no reader's browser calls a font server.

The logo is not drawn by the code - the brand system does not allow it to be
recreated. Drop the master artwork in as `ltv/assets/logo.svg` (Content Hub
CH1648971) and it appears in the header; without it the header simply carries
no logo. Both themes live in `theme.py`, with the colours in `config.py`.

**Start in `config.py`.** Everything that is a decision rather than a
calculation lives there: gift bands, age bands, the horizon, minimum cell
sizes, the source-code-to-agency mapping and which agencies carry a fee cap.
Most changes you want to make are a config change, not a code change.

### The figures

Eleven figures, all drawn from the model. Seven carry a slicer: gross LTV,
net LTV and retention slice by age at sign-up; agency cost and value slices by
gift amount; the fee cap, the donors-needed comparison and retention-in-reserve
slice by agency.

A slicer is not a live chart. Every view is drawn up front in `figures.py` and
the page shows one at a time, so there is no chart library, no network call and
nothing recalculated in a reader's browser - what they see is exactly what the
model produced, and it still works offline and when emailed. Printing falls
back to whichever view was on screen.

---

## Data schema

### `data/historic_donors.xlsx`
One row per donor. Required columns:

| Column | Notes |
|---|---|
| `ReportingChannel` | filtered to `F2F` |
| `Inhouse/Agency` | filtered to `AG` |
| `AcquisitionYear` | selects the behaviour window |
| `Age` | age at acquisition |
| `FirstGiftAmount_MonthlyEquiv` | drives the gift band |
| `LatestGiftAmount_MonthlyEquiv` | drives the upgrade uplift |
| `LTV_1yr_Local` | observed first-year value |
| `RetainedMonth3/12/24/36/48/60` | 1 or 0, blank where not yet observable |
| `UpgradedBy12m` | |

### `data/cohort_2026.xlsx`, sheet `data`
One row per 2026 pledge. Required columns:

| Column | Notes |
|---|---|
| `RegularGivingPledgeSourceCode` | mapped to agency via `config.SOURCE_CODE_MAP` |
| `RegularGivingPledgeGiftAmount` | |
| `RegularGivingPledgeFrequency` | `M`, `Q`, `SA` or `A` |
| `RegularGivingPledgeDate` | |
| `Age` | age at acquisition |

### Annualising

The cost file covers the first half of the year, so volumes are doubled
(`config.ANNUALISE = 2.0`) to describe a full year of acquisition. If a
full-year cost file is supplied, set it to `1.0`. It scales donor counts and
therefore income and cost totals; it does not touch lifetime values, retention
or fee rates, which are per-donor figures.

### `data/agency_costs.xlsx`
One row per agency, header on the first row. Required: `Partner`,
`Actual CPA factor`, `Actual CPSU factor`, `Sign-Ups`, `Realized Donors`,
`Cost EUR`.

---

## Validation

`python run.py --validate` runs four checks.

**Reconciliation** — rebuilt figures against the published v27 report. The
well-powered bands match within half a percentage point on retention and about
2% on lifetime value:

| Band | 12m retention (model / report) | 10y gross LTV (model / report) |
|---|---|---|
| €10 | 60.2% / 60% | €610 / €607 |
| €15 | 53.7% / 54% | €751 / €750 |
| €20 | 56.4% / 56% | €1,093 / €1,071 |

€25 and €30 differ by roughly 15%, which is inside their confidence intervals —
both rest on fewer than 500 historic donors.

**Holdout** — refits the projection on years 1–3 and predicts years 4 and 5,
which are observed. Lands within 0.6 to 5.6 percentage points depending on age
band, worst at 65+.

**Sensitivity** — re-runs the model under eleven stresses: tail retention cut
10% and 20%, years 6–10 cut 10% and 20%, upgrades halved and removed,
mortality applied, 3.5% real discounting, all three combined, a five-year
horizon, and a cruder projection method.

> €20 came out as the best acquisition value in **every** scenario. Total net
> income moved between roughly €1.3m and €4.0m across the same range.
> Argue confidently about *which ask and which agency*; be careful about
> *how much*.

**Precision** — bootstraps each band. €10, €15 and €20 sit within about 4–6%;
€5, €12–13, €25 and €30 are 19% or wider and should be read as indicative.

---

## Known limitations

- **Acquisition cost only.** Development, stewardship and servicing are not
  deducted, so these are not fully loaded margins.
- **No mortality or inflation.** Both are tested in the sensitivity run but
  excluded from the headline figures; they work in opposite directions and
  roughly offset. The 65+ band should be read as an upper bound.
- **Behaviour cannot be split by agency.** The historic data carries no agency
  identifier, so differences between agencies come from what they charge and
  who they approach, not from how their donors behave afterwards.
- **Self-selection.** Everyone in the data chose their own gift amount. The
  model cannot show what happens when a donor is asked for more than they
  would have chosen.
- **Uneven coverage.** Some agencies are represented by only part of the year
  in the donor extract; volumes are scaled to the realised-donor counts in the
  cost file to compensate.
- **Non-monthly donors** use fixed retention schedules rather than the
  observed flags, for the reason given above. Those schedules are an input,
  set in `config.FREQUENCY_RETENTION`, not something the model derives — so
  they are only as good as the numbers supplied.

---

## Narrative and the number audit

The report's prose is **not** in the code. It lives in `data/content.json`,
extracted from an existing report with `python run.py --extract`. The builder
supplies only numbers, charts and tables.

This matters: an earlier version of this model embedded the narrative in the
build script, which made the text hard to edit and let written figures drift
away from the model as it was re-run. `python run.py --audit` flags every euro
amount in the narrative that no longer matches a model output — a prompt to
check, not a list of errors.

---

## Requirements

Python 3.10+, `pandas`, `numpy`, `scipy`, `openpyxl`, `beautifulsoup4`.
No internet access needed at runtime; generated HTML is self-contained with no
external dependencies, so it works offline and when emailed.

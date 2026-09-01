# NovaPay Marketing Experiment Engine

A geo-experiment and causal-inference pipeline built to answer one question
a marketing analytics team actually gets asked:

> **"Should we increase Google Ads spend in this market?"**

This project reframes that into the two questions that actually matter:

1. **Will increasing the budget generate *incremental* conversions** -- not
   just conversions that would have happened anyway?
2. **If so, are those incremental conversions economically worth it** --
   once acquisition cost, retention, and lifetime value are accounted for?

NovaPay is a fictional European fintech. The dataset is synthetic (with a
hidden ground-truth treatment effect this analysis was blind-tested
against), but every method, script, and number below is real and
reproducible from the files in this repo.

---

## The setup

| | |
|---|---|
| Granularity | Weekly |
| Time range | 104 weeks (~2 years) |
| Cities | Berlin (treatment), Munich, Hamburg, Cologne, Frankfurt, Stuttgart (donor pool) |
| Channels | Google Ads, Meta, Email, Organic, Affiliate |
| Intervention | Berlin's Google Ads spend increased ~88% for the final 12 weeks |
| Treatment start | 2025-10-06 |

No city was a convincing off-the-shelf counterfactual for Berlin (different
market size, different baseline trajectory), so the core method is a
**synthetic control**: a weighted blend of the other five cities,
constructed to track Berlin's *pre-treatment* trend as closely as possible.
Once that synthetic "twin" is built, the gap between Berlin's actual
post-treatment numbers and its synthetic twin's numbers is the estimated
effect.

---

## Methodology, in order

1. **Synthetic control fitting** (`python/02_synthetic_control.py`) --
   each city indexed to its own pre-treatment mean (=100) to avoid a
   convex-hull problem (Berlin's raw baseline is larger than any donor
   city, so no non-negative weighted combination of donors could reach it
   on raw levels). Weights fit via constrained optimization
   (`scipy.optimize.minimize`) to minimize pre-treatment RMSE.

2. **Placebo testing** (`python/03_placebo_tests.py`) -- the same
   synthetic-control procedure is re-run treating each *other* city as if
   it were the treated one. If untreated cities can produce gaps just as
   large as Berlin's, the result is likely method noise, not a real effect.
   Produces a rank-based permutation p-value.

3. **Bootstrap confidence interval** (`python/04_experiment_statistics.py`)
   -- resamples the 12 post-treatment weekly gaps to quantify how much the
   *within-Berlin* estimate wobbles week to week. This is a different
   question from the placebo test and does not replace it (see
   Limitations).

4. **Cohort retention check** (`python/05_economics.py`) -- do the
   incremental customers acquired during the treatment window stick around
   at the same rate as normal customers? Tested via permutation test on
   week-4 active-customer fractions, comparing treatment-window cohorts to
   a **time-matched** (not full 2-year history) pre-treatment cohort group,
   specifically to avoid confounding the retention comparison with
   unrelated secular market trends.

5. **Two-layer economics** (`python/05_economics.py`) -- reported as an
   observed floor (confirmed data only) and a separate, explicitly labeled
   projection (extrapolated, resting on an assumption). Never blended into
   one number.

6. **SQL verification layer** (`sql/`) -- the same data-quality, weekly
   rollup, channel metrics, and experiment-input-prep logic, written as SQL
   and verified to actually execute against the CSVs via DuckDB (not just
   written and assumed correct).

7. **AI decision-review layer** (`llm/`) -- a structured LLM reviewer that
   consumes the evidence package above and produces a decision
   recommendation, encoding 7 explicit rules designed to catch the specific
   reasoning traps this project surfaced during development (see below).

---

## Key results

### Causal validity

| City | Role | Pre-treatment fit weight |
|---|---|---:|
| Hamburg | donor | 0.498 |
| Munich | donor | 0.324 |
| Frankfurt | donor | 0.134 |
| Stuttgart | donor | 0.043 |
| Cologne | donor | 0.002 |

Pre-treatment RMSE: **3.29 index points** (tight fit).

| City (placebo rank) | Avg. post-treatment gap (customers/week) |
|---|---:|
| **Berlin (real treatment)** | **+54.8** |
| Munich | +13.3 |
| Hamburg | +5.0 |
| Frankfurt | +1.8 |
| Stuttgart | -1.3 |
| Cologne | -19.0 |

Berlin ranks #1 of 6 by gap magnitude -- but with only 6 units total, the
best possible permutation p-value this test can ever produce is **1/6 =
0.167**, which is exactly what we got. That's a structural power limit, not
a fixable data problem.

### Statistical evidence

- Point estimate: **+54.8 incremental customers/week**
- Bootstrap 95% CI: **[45.2, 65.3]** (within-Berlin week-to-week noise only
  -- does not resolve the cross-city placebo uncertainty above; both are
  reported together deliberately, see Limitations)
- Retention gap: treatment-window cohorts **61.0%** active at week 4 vs.
  **74.2%** for time-matched pre-treatment cohorts (n=8 vs n=8) -- a
  **-13.2 percentage point** gap, permutation p-value **0.00011**

### Economics (two layers, always reported separately)

| | Observed floor (confirmed) | Projected (52-wk, extrapolated) |
|---|---:|---:|
| Incremental customers | 657 | 657 |
| Incremental spend | EUR 104,367 | EUR 104,367 |
| iCAC | EUR 158.76 | EUR 158.76 (unchanged -- iCAC doesn't move with retention) |
| Incremental revenue | EUR 205,800 | EUR 378,696 |
| Incremental contribution | EUR 90,552 | EUR 166,626 |
| iROAS | 1.97x | 3.63x |
| vs. breakeven | **BELOW** | **ABOVE** |

The projected layer rests on one explicit, load-bearing assumption:
**constant decay rate**, extrapolated from only 4 weeks of observed data
out to 52 weeks. Treatment-window cohorts decay faster (0.623/4wk) than
matched pre-treatment cohorts (0.754/4wk) -- the "marginal customer,
lower quality" hypothesis this project was deliberately designed to test.

---

## The decision

```
Recommendation:          GATHER MORE EVIDENCE
Causal validity:         MODERATE
Statistical evidence:    WEAK-TO-MODERATE
Economic attractiveness: UNCERTAIN
```

**Why not stronger:**
- **Causal validity is MODERATE, not STRONG** -- the placebo test result is
  genuinely good, but there is no documented rationale for why Berlin was
  selected as the treatment city. If it was chosen because it was already
  trending well, that's a selection-bias risk the placebo test can't catch.
- **Statistical evidence is WEAK-TO-MODERATE** -- the acquisition effect
  (p=0.167) is structurally incapable of reaching conventional significance
  with only 6 cities. The retention gap is genuinely strong on its own
  (p=0.0001) but is built on only 8 cohorts.
- **Economic attractiveness is UNCERTAIN, not ATTRACTIVE** -- the only
  *confirmed* number says below breakeven. The number that clears
  breakeven is an extrapolation resting on an unverified assumption.

**Recommended next action:** hold current spend, let the existing
treatment cohorts age to real (non-projected) week-8 and week-12 data
before deciding, and get leadership to define an explicit contribution
hurdle rather than defaulting to simple breakeven.

---

## The AI-augmented decision layer

`llm/` contains a structured LLM reviewer designed to reproduce this kind
of disciplined, multi-axis reasoning automatically -- given a JSON evidence
package, not the freeform conversation history.

- `evidence_schema.json` -- the structured input format
- `evidence_novapay_real.json` -- this project's actual results, in that format
- `reviewer_system_prompt.md` -- 7 explicit rules, each one a specific
  reasoning trap this project surfaced during development (e.g. "not
  significant" is not "no effect"; iCAC and CLV answer different questions;
  observed and projected economics must never be blended)
- `test_cases.json` -- 8 adversarial evidence packages, each engineered to
  trip one specific rule, plus one "positive control" case to confirm the
  reviewer doesn't just default to reflexive caution
- `run_reviewer.py` -- calls the Anthropic API with the system prompt against
  any evidence package
- `manual_validation_log.md` -- **honesty note:** the sandbox this project
  was built in had no live API key available, so the prompt was verified by
  manually reasoning through 3 of the 8 test cases (including the sharpest
  one -- excellent statistical fit paired with an undocumented selection
  decision) rather than via automated API calls. Before relying on this in
  a live demo, run `python run_reviewer.py --all-test-cases` with a real key.

---

## Limitations (floor, not truth)

- **Treatment city selection was never documented.** Berlin's selection
  rationale is unknown -- a real selection-bias risk the placebo test
  cannot detect.
- **Structural power ceiling.** With 6 cities, the placebo test can never
  reach p<0.05 regardless of true effect size.
- **Retention gap rests on 8 cohorts.** Directionally strong and
  statistically significant, but a small sample -- one unusual week could
  move the average.
- **The 52-week LTV projection assumes a constant decay rate** from only 4
  weeks of real data. If churn accelerates or decelerates later, this
  number moves substantially.
- **No seasonality stress-test.** The treatment window falls in
  Oct-Dec; any Berlin-specific holiday demand shift not captured by the
  synthetic control could be inflating the apparent effect. This was
  never explicitly tested.
- **iROAS and LTV:CAC came out numerically identical (3.63x) in the
  projected layer** -- a mechanical artifact of using the same revenue
  window for both, not two independent confirmations of the same result.
- **The LLM reviewer was manually verified on 3 of 8 test cases**, not
  tested against the live API end-to-end (see above).

---

## Project structure

```
nova-pay-marketing-experiment-engine/
├── data/                        # city_metrics, channel_performance, cohort_retention CSVs
├── python/                      # 01-06, run in order, tested end-to-end
├── sql/                         # 01-04, verified against the CSVs via DuckDB
├── llm/                         # schema, system prompt, test cases, reviewer script
├── outputs/
│   ├── charts/                  # 5 PNGs
│   └── *.json                   # synthetic control weights, placebo results,
│                                 # experiment statistics, retention results, economics
├── requirements.txt
└── README.md
```

## How to run

```bash
pip install -r requirements.txt

# core pipeline, in order
cd python
python 01_data_exploration.py
python 02_synthetic_control.py
python 03_placebo_tests.py
python 04_experiment_statistics.py
python 05_economics.py
python 06_visualizations.py

# SQL verification (optional, requires duckdb)
cd ../sql
python3 -c "
import duckdb
con = duckdb.connect()
for t in ['city_metrics', 'channel_performance', 'cohort_retention']:
    con.execute(f\"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('../data/{t}.csv')\")
print(con.execute(open('01_data_quality.sql').read().split(';')[0]).fetchdf())
"

# LLM reviewer (optional, requires ANTHROPIC_API_KEY)
cd ../llm
export ANTHROPIC_API_KEY=your_key_here
python run_reviewer.py --evidence evidence_novapay_real.json
```

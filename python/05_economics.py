"""
05_economics.py

Full economic evaluation of the treatment effect, in two layers:

  1. OBSERVED FLOOR: cumulative revenue per customer using only the
     data we actually have (weeks 0 and 4 -- the only window with full
     coverage on both treatment and matched pre-treatment cohorts, given
     right-censoring on younger cohorts). This is a confirmed lower bound.

  2. PROJECTED ESTIMATE [Hypothesis - Unverified by Dataset]: extrapolates
     the observed weeks 0-4 decay rate out to a 52-week horizon, assuming
     a CONSTANT decay rate. This is a real assumption, not a fact --
     stated explicitly, not hidden in the number.

Both are reported. Never collapse them into a single "the number."
"""

import os
import json
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

TREATMENT_CITY = "Berlin"
INCREMENTAL_CUSTOMERS = None  # computed from experiment stats
INCREMENTAL_SPEND_PER_WEEK = None  # computed from channel data
TREATMENT_WEEKS = 12


def load_data():
    cr = pd.read_csv(os.path.join(DATA_DIR, "cohort_retention.csv"))
    cr["cohort_week"] = pd.to_datetime(cr["cohort_week"])
    cm = pd.read_csv(os.path.join(DATA_DIR, "city_metrics.csv"))
    cm["week"] = pd.to_datetime(cm["week"])
    channel = pd.read_csv(os.path.join(DATA_DIR, "channel_performance.csv"))
    channel["week"] = pd.to_datetime(channel["week"])
    return cr, cm, channel


def get_treatment_window(cm):
    all_weeks = sorted(cm["week"].unique())
    return all_weeks[-TREATMENT_WEEKS]


def group_stats(cr, city, cohort_weeks, snapshot):
    sub = cr[(cr["city"] == city) & cr["cohort_week"].isin(cohort_weeks) & (cr["weeks_since_acquisition"] == snapshot)]
    active_frac = (sub["active_customers"] / sub["cohort_size"]).mean()
    rev_per_active = (sub["revenue"] / sub["active_customers"]).mean()
    return active_frac, rev_per_active


def cumulative_rev_per_customer(cr, city, cohort_weeks, snapshots=(0, 4)):
    sub = cr[(cr["city"] == city) & cr["cohort_week"].isin(cohort_weeks) & cr["weeks_since_acquisition"].isin(snapshots)]
    per_cohort = sub.groupby("cohort_week").agg(cohort_size=("cohort_size", "first"), revenue=("revenue", "sum"))
    return (per_cohort["revenue"] / per_cohort["cohort_size"]).mean()


def project_ltv(frac0, decay_rate, rev_per_active, horizon_weeks=52, period=4):
    periods = list(range(0, horizon_weeks + 1, period))
    total = 0
    for t in periods:
        active_frac = frac0 * (decay_rate ** (t / period))
        total += active_frac * rev_per_active
    return total


def retention_permutation_test(cr, city, treat_cohorts, pre_cohorts, snapshot=4, n_iter=100_000, seed=42):
    """
    Is the treatment-vs-pre retention gap at a given snapshot bigger than
    what random reshuffling of cohort labels would produce by chance?
    Returns (treat_mean_pct, pre_mean_pct, gap_pp, p_value).
    """
    rng = np.random.default_rng(seed)
    sub_city = cr[cr["city"] == city]

    def active_fracs(cohorts):
        sub = sub_city[sub_city["cohort_week"].isin(cohorts) & (sub_city["weeks_since_acquisition"] == snapshot)]
        return sub.groupby("cohort_week").apply(lambda g: g["active_customers"].sum() / g["cohort_size"].sum()).values

    treat_fracs = active_fracs(treat_cohorts)
    pre_fracs = active_fracs(pre_cohorts)
    observed_gap = (treat_fracs.mean() - pre_fracs.mean()) * 100

    pooled = np.concatenate([treat_fracs, pre_fracs])
    n_treat = len(treat_fracs)
    count_extreme = 0
    for _ in range(n_iter):
        shuffled = rng.permutation(pooled)
        perm_gap = (shuffled[:n_treat].mean() - shuffled[n_treat:].mean()) * 100
        if abs(perm_gap) >= abs(observed_gap):
            count_extreme += 1
    p_value = count_extreme / n_iter

    return treat_fracs.mean() * 100, pre_fracs.mean() * 100, observed_gap, p_value, len(treat_fracs), len(pre_fracs)


if __name__ == "__main__":
    cr, cm, channel = load_data()
    treatment_start = get_treatment_window(cm)

    berlin_cr = cr[cr["city"] == TREATMENT_CITY]
    treat_cohorts = berlin_cr[berlin_cr["cohort_week"] >= treatment_start]["cohort_week"].unique()
    pre_recent_cohorts = sorted(berlin_cr[berlin_cr["cohort_week"] < treatment_start]["cohort_week"].unique())[-len(treat_cohorts):]

    # --- retention significance test: only cohorts with OBSERVED (non-right-censored)
    # week-4 data qualify -- this naturally shrinks treat_cohorts from 12 to 8, since the
    # 4 most recent treatment cohorts haven't aged 4 weeks yet within this dataset's window.
    # Pre-treatment group is re-matched to that same n so the comparison is apples-to-apples.
    treat_cohorts_week4 = sorted(
        berlin_cr[berlin_cr["cohort_week"].isin(treat_cohorts) & (berlin_cr["weeks_since_acquisition"] == 4)]["cohort_week"].unique()
    )
    pre_cohorts_matched_n8 = sorted(berlin_cr[berlin_cr["cohort_week"] < treatment_start]["cohort_week"].unique())[-len(treat_cohorts_week4):]

    # --- core experiment inputs (from earlier scripts' results) ---
    with open(os.path.join(OUT_DIR, "experiment_statistics.json")) as f:
        stats = json.load(f)
    incremental_customers_per_week = stats["point_estimate"]
    incremental_customers = incremental_customers_per_week * TREATMENT_WEEKS

    google = channel[channel["channel"] == "Google Ads"].copy()
    google["period"] = google["week"].apply(lambda w: "treatment" if w >= treatment_start else "pre")
    berlin_google = google[google["city"] == TREATMENT_CITY]
    spend_by_period = berlin_google.groupby("period")["spend"].mean()
    incremental_spend_per_week = spend_by_period["treatment"] - spend_by_period["pre"]
    incremental_spend = incremental_spend_per_week * TREATMENT_WEEKS

    contribution_margin = cm[cm.city == TREATMENT_CITY]["contribution_margin"].iloc[0]
    iCAC = incremental_spend / incremental_customers

    # --- LAYER 1: observed floor (weeks 0+4, confirmed data) ---
    rev_per_cust_treatment_floor = cumulative_rev_per_customer(cr, TREATMENT_CITY, treat_cohorts)
    rev_per_cust_pre_floor = cumulative_rev_per_customer(cr, TREATMENT_CITY, pre_recent_cohorts)

    incremental_revenue_floor = incremental_customers * rev_per_cust_treatment_floor
    contribution_floor = incremental_revenue_floor * contribution_margin
    iROAS_floor = incremental_revenue_floor / incremental_spend

    # --- LAYER 2: projected estimate (52-week, extrapolated, HYPOTHESIS) ---
    treat_frac0, treat_rev_active0 = group_stats(cr, TREATMENT_CITY, treat_cohorts, 0)
    treat_frac4, treat_rev_active4 = group_stats(cr, TREATMENT_CITY, treat_cohorts, 4)
    r_treatment = treat_frac4 / treat_frac0

    pre_frac0, pre_rev_active0 = group_stats(cr, TREATMENT_CITY, pre_recent_cohorts, 0)
    pre_frac4, pre_rev_active4 = group_stats(cr, TREATMENT_CITY, pre_recent_cohorts, 4)
    r_pre = pre_frac4 / pre_frac0

    avg_rev_active = np.mean([treat_rev_active0, treat_rev_active4, pre_rev_active0, pre_rev_active4])

    ltv_treatment_projected = project_ltv(treat_frac0, r_treatment, avg_rev_active)
    ltv_pre_projected = project_ltv(pre_frac0, r_pre, avg_rev_active)

    incremental_revenue_projected = incremental_customers * ltv_treatment_projected
    contribution_projected = incremental_revenue_projected * contribution_margin
    iROAS_projected = incremental_revenue_projected / incremental_spend
    ltv_cac_projected = ltv_treatment_projected / iCAC

    # --- report ---
    print(f"Incremental customers ({TREATMENT_WEEKS} wks): {incremental_customers:.0f}")
    print(f"Incremental spend ({TREATMENT_WEEKS} wks): EUR {incremental_spend:,.0f}")
    print(f"iCAC: EUR {iCAC:.2f}")
    print(f"Contribution margin: {contribution_margin:.1%}")

    print(f"\n=== LAYER 1: OBSERVED FLOOR (confirmed, weeks 0-4) ===")
    print(f"Revenue/customer: EUR {rev_per_cust_treatment_floor:.2f}")
    print(f"Incremental revenue: EUR {incremental_revenue_floor:,.0f}")
    print(f"Incremental contribution: EUR {contribution_floor:,.0f}")
    print(f"iROAS: {iROAS_floor:.2f}x")
    print(f"vs. spend (EUR {incremental_spend:,.0f}): {'ABOVE' if contribution_floor > incremental_spend else 'BELOW'} breakeven")

    print(f"\n=== LAYER 2: PROJECTED [Hypothesis - Unverified by Dataset] (52-wk, extrapolated) ===")
    print(f"Decay rate/4wk -- treatment: {r_treatment:.4f} | matched pre: {r_pre:.4f}")
    print(f"Projected LTV/customer: EUR {ltv_treatment_projected:.2f} (vs EUR {ltv_pre_projected:.2f} if no retention penalty)")
    print(f"Incremental revenue (projected): EUR {incremental_revenue_projected:,.0f}")
    print(f"Incremental contribution (projected): EUR {contribution_projected:,.0f}")
    print(f"iROAS (projected): {iROAS_projected:.2f}x | LTV:CAC (projected): {ltv_cac_projected:.2f}x")
    print(f"vs. spend: {'ABOVE' if contribution_projected > incremental_spend else 'BELOW'} breakeven")

    # --- retention significance test (permutation, week-4 snapshot) ---
    treat_ret_pct, pre_ret_pct, ret_gap_pp, ret_p_value, n_treat, n_pre = retention_permutation_test(
        cr, TREATMENT_CITY, treat_cohorts_week4, pre_cohorts_matched_n8, snapshot=4
    )
    print(f"\n=== RETENTION SIGNIFICANCE CHECK (week-4 snapshot, permutation test) ===")
    print(f"Treatment-window cohorts:  {treat_ret_pct:.1f}% active  (n={n_treat})")
    print(f"Time-matched pre cohorts:  {pre_ret_pct:.1f}% active  (n={n_pre})")
    print(f"Gap: {ret_gap_pp:.1f} percentage points | permutation p-value: {ret_p_value:.5f}")

    retention_results = {
        "method": "permutation test, 100000 reshuffles of pooled treatment+pre-treatment cohort labels",
        "snapshot": "weeks_since_acquisition == 4",
        "treatment_cohorts_n": int(n_treat),
        "pre_treatment_cohorts_n": int(n_pre),
        "treatment_retention_pct": float(treat_ret_pct),
        "pre_treatment_retention_pct": float(pre_ret_pct),
        "gap_percentage_points": float(ret_gap_pp),
        "p_value": float(ret_p_value),
        "note": "pre-treatment cohorts are TIME-MATCHED (n most recent pre-treatment cohorts, not full 2-year history) to avoid confounding with secular market trends",
    }
    with open(os.path.join(OUT_DIR, "retention_results.json"), "w") as f:
        json.dump(retention_results, f, indent=2)
    print(f"Saved: {OUT_DIR}/retention_results.json")

    results = {
        "incremental_customers": float(incremental_customers),
        "incremental_spend": float(incremental_spend),
        "iCAC": float(iCAC),
        "contribution_margin": float(contribution_margin),
        "observed_floor": {
            "incremental_revenue": float(incremental_revenue_floor),
            "incremental_contribution": float(contribution_floor),
            "iROAS": float(iROAS_floor),
            "above_breakeven": bool(contribution_floor > incremental_spend),
        },
        "projected_52wk_hypothesis": {
            "decay_rate_treatment": float(r_treatment),
            "decay_rate_matched_pre": float(r_pre),
            "ltv_per_customer": float(ltv_treatment_projected),
            "incremental_revenue": float(incremental_revenue_projected),
            "incremental_contribution": float(contribution_projected),
            "iROAS": float(iROAS_projected),
            "ltv_cac": float(ltv_cac_projected),
            "above_breakeven": bool(contribution_projected > incremental_spend),
        },
    }
    with open(os.path.join(OUT_DIR, "economics_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {OUT_DIR}/economics_results.json")

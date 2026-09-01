"""
03_placebo_tests.py

Causal validity check: pretend each NON-treated city was treated, fit a
synthetic control for it (using only the OTHER cities as donors, excluding
the real treated city), and compare its "fake gap" to the real treated
city's gap. If untreated cities can produce gaps just as large, the real
result may just be noise our method is prone to generating -- not evidence
of a real effect.

Produces a rank-based (permutation) p-value: how many cities (out of all
6, treated + 5 placebos) show the largest |gap|? If the real treated city
ranks #1, that's evidence -- but with only 6 units, the best possible
p-value here is 1/6 (~0.167), a structural power limit worth stating
explicitly.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from importlib import import_module
sc = import_module("02_synthetic_control")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "charts")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

TREATMENT_CITY = "Berlin"


def run_placebo_tests(pivot, treatment_start, treated=TREATMENT_CITY):
    all_cities = list(pivot.columns)
    placebo_cities = [c for c in all_cities if c != treated]

    real_result = sc.fit_synthetic_control(pivot, treatment_start, treated=treated)

    placebo_results = {}
    for pc in placebo_cities:
        donor_pool = [c for c in all_cities if c not in (treated, pc)]
        placebo_results[pc] = sc.fit_synthetic_control(pivot, treatment_start, treated=pc, donors=donor_pool)

    return real_result, placebo_results


def summarize_and_rank(pivot, treatment_start, real_result, placebo_results, treated=TREATMENT_CITY):
    post_mask = pivot.index >= treatment_start
    gaps = {treated: real_result["gap"][post_mask].mean()}
    fits = {treated: real_result["pre_rmse"]}
    for pc, r in placebo_results.items():
        gaps[pc] = r["gap"][post_mask].mean()
        fits[pc] = r["pre_rmse"]

    print(f"{'City':<12}{'Pre-RMSE':<12}{'Avg post-gap':<15}")
    for c in gaps:
        marker = "  <-- real treated" if c == treated else ""
        print(f"{c:<12}{fits[c]:<12.2f}{gaps[c]:<15.1f}{marker}")

    ranked = sorted(gaps.items(), key=lambda x: -abs(x[1]))
    treated_rank = [i for i, (c, g) in enumerate(ranked, 1) if c == treated][0]
    n = len(gaps)
    p_value = treated_rank / n
    print(f"\n{treated} rank: {treated_rank} of {n} (by |gap|)")
    print(f"Permutation p-value: {p_value:.3f}  (best possible with n={n} units: {1/n:.3f})")

    return gaps, p_value


def plot_placebo_distribution(pivot, real_result, placebo_results, treatment_start, treated=TREATMENT_CITY):
    fig, ax = plt.subplots(figsize=(12, 6))
    for pc, r in placebo_results.items():
        ax.plot(pivot.index, r["gap"], color="gray", alpha=0.5, linewidth=1)
    ax.plot(pivot.index, real_result["gap"], color="tab:red", linewidth=2.5, label=f"{treated} (real treatment)")
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=treatment_start, color="black", linestyle=":", label="Treatment start")
    ax.legend(loc="upper left")
    ax.set_title(f"Gap (Actual - Synthetic): {treated} vs. all placebo cities")
    ax.set_ylabel("Gap in new customers")
    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "03_placebo_gap_plot.png")
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"Saved chart: {out_path}")


if __name__ == "__main__":
    pivot, treatment_start = sc.load_pivot()
    real_result, placebo_results = run_placebo_tests(pivot, treatment_start)
    gaps, p_value = summarize_and_rank(pivot, treatment_start, real_result, placebo_results)
    plot_placebo_distribution(pivot, real_result, placebo_results, treatment_start)

    import json
    with open(os.path.join(OUT_DIR, "placebo_results.json"), "w") as f:
        json.dump({"gaps": gaps, "p_value": p_value}, f, indent=2)
    print(f"\nSaved: {OUT_DIR}/placebo_results.json")

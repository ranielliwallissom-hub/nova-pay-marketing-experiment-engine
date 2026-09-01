"""
06_visualizations.py

Final two charts for the README/report:
  1. Retention decay curves: treatment-window cohorts vs. matched
     pre-treatment cohorts, observed points + projected extrapolation.
  2. Economics comparison: observed floor vs. projected estimate,
     against the incremental spend breakeven line.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
CHARTS_DIR = os.path.join(OUT_DIR, "charts")


def plot_retention_curves():
    with open(os.path.join(OUT_DIR, "economics_results.json")) as f:
        econ = json.load(f)
    r_treat = econ["projected_52wk_hypothesis"]["decay_rate_treatment"]
    r_pre = econ["projected_52wk_hypothesis"]["decay_rate_matched_pre"]

    weeks = np.arange(0, 53, 1)
    treat_curve = r_treat ** (weeks / 4)
    pre_curve = r_pre ** (weeks / 4)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(weeks, pre_curve * 100, label="Matched pre-treatment cohorts", color="tab:blue")
    ax.plot(weeks, treat_curve * 100, label="Treatment-window cohorts", color="tab:red")
    ax.axvspan(0, 8, alpha=0.1, color="gray", label="Observed window")
    ax.axvline(x=8, color="gray", linestyle=":")
    ax.set_xlabel("Weeks since acquisition")
    ax.set_ylabel("% of cohort still active")
    ax.set_title("Retention decay: observed (0-8 wks) vs. projected extrapolation")
    ax.legend()
    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "06a_retention_curves.png")
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_economics_comparison():
    with open(os.path.join(OUT_DIR, "economics_results.json")) as f:
        econ = json.load(f)

    labels = ["Observed floor\n(weeks 0-4, confirmed)", "Projected\n(52-wk, hypothesis)"]
    values = [econ["observed_floor"]["incremental_contribution"],
              econ["projected_52wk_hypothesis"]["incremental_contribution"]]
    spend = econ["incremental_spend"]

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["tab:red" if v < spend else "tab:green" for v in values]
    ax.bar(labels, values, color=colors, alpha=0.8)
    ax.axhline(y=spend, color="black", linestyle="--", label=f"Incremental spend (breakeven line): EUR {spend:,.0f}")
    ax.set_ylabel("Incremental contribution (EUR)")
    ax.set_title("Incremental contribution vs. breakeven")
    ax.legend()
    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "06b_economics_comparison.png")
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    plot_retention_curves()
    plot_economics_comparison()

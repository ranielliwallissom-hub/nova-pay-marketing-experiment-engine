"""
02_synthetic_control.py

Fit synthetic control weights for the treatment city, using ONLY
pre-treatment data. Cities are matched on their INDEXED series
(each city rescaled to its own pre-treatment average = 100) rather than
raw levels, because a convex combination (weights >= 0, sum to 1) can
never exceed the largest donor's raw level -- see README for the full
explanation of this "convex hull" limitation.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "charts")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

TREATMENT_CITY = "Berlin"
TREATMENT_WEEKS = 12


def load_pivot():
    city = pd.read_csv(os.path.join(DATA_DIR, "city_metrics.csv"))
    city["week"] = pd.to_datetime(city["week"])
    pivot = city.pivot_table(index="week", columns="city", values="new_customers")
    all_weeks = sorted(pivot.index)
    treatment_start = all_weeks[-TREATMENT_WEEKS]
    return pivot, treatment_start


def fit_synthetic_control(pivot, treatment_start, treated=TREATMENT_CITY, donors=None):
    all_cities = list(pivot.columns)
    if donors is None:
        donors = [c for c in all_cities if c != treated]

    pre_mask = pivot.index < treatment_start
    pre_means = pivot.loc[pre_mask].mean()
    indexed = pivot / pre_means * 100

    treated_pre = indexed.loc[pre_mask, treated].values
    donor_pre = indexed.loc[pre_mask, donors].values

    def objective(w):
        return np.sum((treated_pre - donor_pre @ w) ** 2)

    n = len(donors)
    w0 = np.repeat(1 / n, n)
    bounds = [(0, 1)] * n
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    result = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=constraints)

    weights = dict(zip(donors, result.x.round(4)))
    pre_rmse = np.sqrt(np.mean((treated_pre - donor_pre @ result.x) ** 2))

    synth_idx_full = indexed[donors].values @ result.x
    synth_customers = synth_idx_full / 100 * pre_means[treated]
    gap = pivot[treated].values - synth_customers

    return {
        "weights": weights,
        "pre_rmse": pre_rmse,
        "synthetic_series": synth_customers,
        "gap": gap,
        "success": result.success,
    }


def plot_actual_vs_synthetic(pivot, treatment_start, result, treated=TREATMENT_CITY):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(pivot.index, pivot[treated], label=f"Actual {treated}", color="tab:blue", linewidth=2)
    ax.plot(pivot.index, result["synthetic_series"], label=f"Synthetic {treated}",
            color="tab:orange", linestyle="--", linewidth=2)
    ax.axvline(x=treatment_start, color="black", linestyle=":", label="Treatment start")
    ax.legend()
    ax.set_title(f"Actual vs. Synthetic {treated}")
    ax.set_ylabel("New customers")
    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "02_actual_vs_synthetic.png")
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"Saved chart: {out_path}")


if __name__ == "__main__":
    pivot, treatment_start = load_pivot()
    result = fit_synthetic_control(pivot, treatment_start)

    print(f"Optimization success: {result['success']}")
    print(f"Pre-treatment RMSE (index points): {result['pre_rmse']:.2f}")
    print("\nSynthetic control weights:")
    for city, w in sorted(result["weights"].items(), key=lambda x: -x[1]):
        print(f"  {city:12s} {w:.3f}")

    plot_actual_vs_synthetic(pivot, treatment_start, result)

    # save results for downstream scripts (03, 04, 05)
    np.save(os.path.join(OUT_DIR, "berlin_gap.npy"), result["gap"])
    with open(os.path.join(OUT_DIR, "synthetic_control_weights.json"), "w") as f:
        json.dump({"weights": result["weights"], "pre_rmse": float(result["pre_rmse"]),
                    "treatment_start": treatment_start.date().isoformat()}, f, indent=2)
    print(f"\nSaved: {OUT_DIR}/berlin_gap.npy, synthetic_control_weights.json")

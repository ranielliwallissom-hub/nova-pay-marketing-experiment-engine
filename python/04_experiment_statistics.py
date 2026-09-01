"""
04_experiment_statistics.py

Bootstrap confidence interval on the treatment effect.

We resample the 12 observed post-treatment weekly gaps WITH replacement,
10,000 times, and take the 2.5th/97.5th percentiles of the resulting
distribution of means as a 95% CI.

LIMITATION (stated explicitly, not hidden): this only captures week-to-week
noise within the 12 treatment weeks. It does NOT capture uncertainty from
how the synthetic control weights themselves were fit. A more advanced
approach would also resample/refit across donor cities. This is a
documented simplification, appropriate for a portfolio-scale project.
"""

import os
import numpy as np

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
N_BOOTSTRAP = 10_000
SEED = 42


def bootstrap_ci(post_gaps, n_boot=N_BOOTSTRAP, seed=SEED):
    rng = np.random.default_rng(seed)
    boot_means = np.zeros(n_boot)
    for i in range(n_boot):
        resample = rng.choice(post_gaps, size=len(post_gaps), replace=True)
        boot_means[i] = resample.mean()
    ci_lower = np.percentile(boot_means, 2.5)
    ci_upper = np.percentile(boot_means, 97.5)
    return ci_lower, ci_upper, boot_means


if __name__ == "__main__":
    berlin_gap = np.load(os.path.join(OUT_DIR, "berlin_gap.npy"))
    # last 12 values = post-treatment weeks (matches TREATMENT_WEEKS in script 02)
    post_gaps = berlin_gap[-12:]

    point_estimate = post_gaps.mean()
    ci_lower, ci_upper, boot_means = bootstrap_ci(post_gaps)

    print(f"Point estimate: {point_estimate:.1f} customers/week")
    print(f"95% bootstrap CI: [{ci_lower:.1f}, {ci_upper:.1f}]")
    print(f"Crosses zero: {'YES' if ci_lower < 0 else 'NO'}")
    print("\nNOTE: this CI reflects week-to-week noise only. See placebo test (03)")
    print("for the cross-city uncertainty check -- report both, not just this one.")

    import json
    with open(os.path.join(OUT_DIR, "experiment_statistics.json"), "w") as f:
        json.dump({
            "point_estimate": float(point_estimate),
            "ci_95_lower": float(ci_lower),
            "ci_95_upper": float(ci_upper),
            "method": "bootstrap, resampling 12 post-treatment weekly gaps, n=10000",
            "limitation": "captures within-unit week-to-week noise only, not synthetic-control weight uncertainty",
        }, f, indent=2)
    print(f"\nSaved: {OUT_DIR}/experiment_statistics.json")

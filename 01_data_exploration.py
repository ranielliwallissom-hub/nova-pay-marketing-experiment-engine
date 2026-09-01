"""
01_data_exploration.py

Load the NovaPay marketing data, do a basic quality audit, and produce the
first visual check: weekly new customers by city, with the treatment window
marked. This is the "look before you touch anything" step -- it should
always run before any modeling.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CHARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

TREATMENT_CITY = "Berlin"
TREATMENT_WEEKS = 12


def load_data():
    city = pd.read_csv(os.path.join(DATA_DIR, "city_metrics.csv"))
    channel = pd.read_csv(os.path.join(DATA_DIR, "channel_performance.csv"))
    city["week"] = pd.to_datetime(city["week"])
    channel["week"] = pd.to_datetime(channel["week"])
    return city, channel


def audit(city, channel):
    print("=== city_metrics: shape, dtypes, nulls ===")
    print(city.shape)
    print(city.dtypes)
    print("nulls:", city.isnull().sum().sum())
    print("duplicate (week, city) keys:", city.duplicated(subset=["week", "city"]).sum())

    print("\n=== channel_performance: shape, dtypes, nulls ===")
    print(channel.shape)
    print("nulls:", channel.isnull().sum().sum())
    print("duplicate (week, city, channel) keys:",
          channel.duplicated(subset=["week", "city", "channel"]).sum())

    cm_keys = set(zip(city.week, city.city))
    cp_keys = set(zip(channel.week, channel.city))
    print("\njoin key check (week+city) -- orphans each direction:",
          len(cm_keys - cp_keys), len(cp_keys - cm_keys))


def get_treatment_start(city):
    all_weeks = sorted(city["week"].unique())
    return all_weeks[-TREATMENT_WEEKS]


def plot_weekly_customers(city, treatment_start):
    pivot = city.pivot_table(index="week", columns="city", values="new_customers")
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(ax=ax)
    ax.axvline(x=treatment_start, color="black", linestyle="--", label="Treatment start")
    ax.legend()
    ax.set_title("Weekly new customers by city")
    ax.set_ylabel("New customers")
    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "01_weekly_customers_by_city.png")
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"\nSaved chart: {out_path}")


def spend_pre_vs_treatment(channel, treatment_start):
    google = channel[channel["channel"] == "Google Ads"].copy()
    google["period"] = google["week"].apply(lambda w: "treatment" if w >= treatment_start else "pre")
    summary = google.groupby(["city", "period"])["spend"].mean().round(0)
    print("\n=== Avg weekly Google Ads spend, pre vs. treatment ===")
    print(summary)
    return summary


if __name__ == "__main__":
    city, channel = load_data()
    audit(city, channel)
    treatment_start = get_treatment_start(city)
    print(f"\nTreatment start date: {treatment_start.date()}")
    plot_weekly_customers(city, treatment_start)
    spend_pre_vs_treatment(channel, treatment_start)

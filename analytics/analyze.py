#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from analyze import load_logs, build_dataframe, _bar_labels, STATUS_COLORS, PAL, DPI

OUTPUT_DIR = Path(__file__).parent
BETTERSTACK_UA = "Better Stack Better Uptime Bot"


def _save(fig, name):
    fig.savefig(
        OUTPUT_DIR / f"{name}.png", dpi=DPI, bbox_inches="tight", facecolor="white"
    )
    plt.close(fig)
    print(f"  ✓ {name}.png")


def plot_status_codes(df, suffix=""):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    cc = df["status_class"].value_counts().sort_index()
    axes[0].pie(
        cc,
        labels=cc.index,
        autopct="%1.1f%%",
        colors=[STATUS_COLORS.get(c, "#ccc") for c in cc.index],
        startangle=90,
    )
    axes[0].set_title("Triedy stavových kódov")

    top = df["status"].value_counts().head(10)
    labels = top.index.astype(str)
    sns.barplot(
        x=top.values,
        y=labels,
        hue=labels,
        ax=axes[1],
        palette="viridis",
        orient="h",
        legend=False,
    )
    axes[1].set(title="Najčastejšie stavové kódy", xlabel="Počet", ylabel="")
    _bar_labels(axes[1], top.values, fontsize=8)

    fig.tight_layout()
    _save(fig, f"03_status_codes{suffix}")


def plot_response_times(df, suffix=""):
    rt = df["request_time"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].hist(
        rt[rt <= rt.quantile(0.95)], bins=80, color=PAL[3], edgecolor="white", lw=0.3
    )
    axes[0].axvline(
        rt.median(), color="red", ls="--", lw=1, label=f"medián={rt.median():.3f}s"
    )
    axes[0].set(title="Čas odpovede (≤p95)", xlabel="Sekundy", ylabel="Počet")
    axes[0].legend()

    percs = [50, 75, 90, 95, 99, 99.9]
    vals = [np.percentile(rt, p) for p in percs]
    axes[1].barh([f"p{p}" for p in percs], vals, color=PAL[4])
    axes[1].set(title="Percentily času odpovede", xlabel="Sekundy")
    _bar_labels(axes[1], vals, fmt="{:.3f}s", fontsize=8)

    fig.tight_layout()
    _save(fig, f"04_response_times{suffix}")


def plot_top_paths(df, suffix=""):
    top = df["path"].value_counts().head(20)
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.barplot(
        x=top.values,
        y=top.index,
        hue=top.index,
        ax=ax,
        palette="rocket_r",
        orient="h",
        legend=False,
    )
    ax.set(title="20 najčastejších ciest", xlabel="Požiadavky", ylabel="")
    ax.tick_params(axis="y", labelsize=8)
    _bar_labels(ax, top.values)
    fig.tight_layout()
    _save(fig, f"05_top_paths{suffix}")


def plot_user_agents(df, suffix=""):
    ua = df["http_user_agent"].str.extract(
        r"(Chrome|Firefox|Safari|Edge|bot|curl|python|Go-http|wget)", expand=False
    )
    ua = ua.fillna("Ostatné").str.lower().value_counts().head(10)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(
        x=ua.values,
        y=ua.index,
        hue=ua.index,
        ax=ax,
        palette="flare",
        orient="h",
        legend=False,
    )
    ax.set(title="Rodiny klientských agentov", xlabel="Požiadavky", ylabel="")
    fig.tight_layout()
    _save(fig, f"11_user_agents{suffix}")


def plot_top_countries(df, suffix=""):
    if (df["country"] == "Unknown").all():
        return

    top = df[df["country"] != "Unknown"]["country"].value_counts().head(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        x=top.values,
        y=top.index,
        hue=top.index,
        ax=ax,
        palette="Spectral",
        orient="h",
        legend=False,
    )
    ax.set(title="15 najčastejších krajín podľa požiadaviek", xlabel="Požiadavky", ylabel="")
    ax.tick_params(axis="y", labelsize=9)
    _bar_labels(ax, top.values)
    fig.tight_layout()
    _save(fig, f"13_top_countries{suffix}")


PLOTS = [
    plot_status_codes,
    plot_response_times,
    plot_top_paths,
    plot_user_agents,
    plot_top_countries,
]


def main():
    records = load_logs()
    if not records:
        print("No log entries found.")
        sys.exit(1)

    print(f"Loaded {len(records):,} entries")
    df = build_dataframe(records)
    df_no_bs = df[~df["http_user_agent"].str.contains(BETTERSTACK_UA, na=False)]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating charts → {OUTPUT_DIR}/")

    for plot_fn in PLOTS:
        plot_fn(df)
        plot_fn(df_no_bs, suffix="_no_betterstack")

    print(f"\nDone — {len(list(OUTPUT_DIR.glob('*.png')))} charts in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

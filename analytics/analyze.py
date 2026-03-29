#!/usr/bin/env python3
"""
{ zcat -f /srv/host/*/logs/access.* /var/log/nginx/* 2>/dev/null; } > access.log
scp root@nocost-dev:~/access.log .
python analyze.py
"""

import json
import sys
from pathlib import Path

import maxminddb
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

SCRIPT_DIR = Path(__file__).parent
LOG_INPUT = SCRIPT_DIR / "access.log"
OUTPUT_DIR = SCRIPT_DIR / "report"
MMDB_PATH = SCRIPT_DIR / "GeoLite2-City.mmdb"
DPI = 150

STATUS_COLORS = {
    "1xx": "#64b5f6",
    "2xx": "#81c784",
    "3xx": "#fff176",
    "4xx": "#ffb74d",
    "5xx": "#e57373",
}

BETTERSTACK_UA = "Better Stack Better Uptime Bot"

sns.set_theme(style="whitegrid", palette="muted", font_scale=0.9)
PAL = sns.color_palette("Set2", 10)


def load_logs() -> list[dict]:
    records = []
    with open(LOG_INPUT, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _lookup_countries(ips: pd.Series) -> dict[str, str]:
    """Resolve unique IPs to country names via MaxMind GeoLite2."""
    if not MMDB_PATH.exists():
        print(
            f"  ⚠ GeoLite2 database not found at {MMDB_PATH}, skipping country lookup"
        )
        return {}

    result = {}
    with maxminddb.open_database(str(MMDB_PATH)) as reader:
        for ip in ips.unique():
            try:
                record = reader.get(ip)
                if record and "country" in record:
                    result[ip] = record["country"]["names"]["en"]
            except (ValueError, KeyError):
                continue
    return result


def build_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["time"], errors="coerce", utc=True)

    for col in ("status", "body_bytes_sent", "request_time", "request_length"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["status"] = df["status"].astype(int)
    df["status_class"] = (
        (df["status"] // 100)
        .map({1: "1xx", 2: "2xx", 3: "3xx", 4: "4xx", 5: "5xx"})
        .fillna("???")
    )
    df["path"] = df["request_uri"].str.split("?").str[0]
    df["hour"] = df["timestamp"].dt.floor("h")
    df["date"] = df["timestamp"].dt.date
    df["weekday"] = df["timestamp"].dt.day_name()
    df["hour_of_day"] = df["timestamp"].dt.hour

    ip_to_country = _lookup_countries(df["remote_addr"])
    df["country"] = df["remote_addr"].map(ip_to_country).fillna("Unknown")

    return df.sort_values("timestamp").reset_index(drop=True)

FIG_I = 1

def _save(fig, name):
    global FIG_I

    fig.savefig(
        OUTPUT_DIR / f"{FIG_I:02d}_{name}.png", dpi=DPI, bbox_inches="tight", facecolor="white"
    )
    plt.close(fig)
    print(f"  ✓ {name}.png")

    if "no_betterstack" in name:
        FIG_I += 1


def _bar_labels(ax, values, fmt="{:,}", fontsize=7):
    max_val = max(values) if len(values) else 0
    for i, v in enumerate(values):
        ax.text(v + max_val * 0.01, i, fmt.format(v), va="center", fontsize=fontsize)


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
    _save(fig, f"status_codes{suffix}")


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
    _save(fig, f"response_times{suffix}")


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
    _save(fig, f"top_paths{suffix}")


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
    _save(fig, f"user_agents{suffix}")


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
    ax.set(
        title="15 najčastejších krajín podľa požiadaviek",
        xlabel="Požiadavky",
        ylabel="",
    )
    ax.tick_params(axis="y", labelsize=9)
    _bar_labels(ax, top.values)
    fig.tight_layout()
    _save(fig, f"top_countries{suffix}")


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
        print(f"No log entries found. Place logs in {LOG_INPUT}")
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

"""Regenerate only the revised 05/06 half-skew charts from existing CSV outputs."""
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd


ROOT = Path(__file__).resolve().parent / "outputs"
TAG = "QUADRATIC_HALF-SKEW_CURVATURE-WING"
COLORS = {"CALL_SKEW": "#2b6cb0", "PUT_SKEW": "#d1495b"}
LABELS = {"CALL_SKEW": "Call Skew", "PUT_SKEW": "Put Skew"}


def render_05() -> int:
    base = ROOT / f"05_skew_curvature_{TAG}"
    data = pd.read_csv(base / "data" / "half_skew_term_structure.csv", parse_dates=["TRADE_DT", "EXPIRY"])
    out_dir = base / "figures" / "half_skew_by_expiry"
    count = 0
    for expiry, sample in data.groupby("EXPIRY", sort=True):
        sample = sample.sort_values("TRADE_DT")
        code = pd.Timestamp(expiry).strftime("%Y%m")
        fig, ax = plt.subplots(figsize=(11, 5.5))
        for metric in ("CALL_SKEW", "PUT_SKEW"):
            ax.plot(sample.TRADE_DT, sample[metric], color=COLORS[metric], marker="o", ms=3.5,
                    lw=1.6, label=LABELS[metric])
        ax.axhline(0, color="#697386", ls="--", lw=.9)
        ax.set_title(f"Call and Put Half Skew - {code} | h={float(sample.HALF_SKEW_H.iloc[0]):.3f}",
                     fontsize=13, fontweight="bold")
        ax.set_xlabel("Trade Date")
        ax.set_ylabel("Half skew (IV difference vs ATM)")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.legend(); ax.grid(color="#d9e0e8", lw=.7, alpha=.8)
        fig.autofmt_xdate(); fig.tight_layout()
        fig.savefig(out_dir / f"half_skew_{code}.png", dpi=170, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        count += 1
    return count


def render_06() -> int:
    base = ROOT / f"06_skew_strategy_{TAG}"
    count = 0
    for csv_path in sorted(base.glob("expiry_*/figures/skew_diagnostics/selected_expiry_half_skew_segments.csv")):
        segments = pd.read_csv(csv_path, parse_dates=["START_DATE", "END_DATE", "EXPIRY"])
        if segments.empty:
            continue
        fig, ax = plt.subplots(figsize=(15, 7.5))
        for start_col, end_col, label, color in (
            ("CALL_SKEW_START", "CALL_SKEW_END", "Call Skew", "#2b6cb0"),
            ("PUT_SKEW_START", "PUT_SKEW_END", "Put Skew", "#d1495b"),
        ):
            for j, row in enumerate(segments.itertuples(index=False)):
                ax.plot([row.START_DATE, row.END_DATE], [getattr(row, start_col), getattr(row, end_col)],
                        marker="o", markersize=4.2, linewidth=2.0, color=color, alpha=.9,
                        label=label if j == 0 else None)
        ax.axhline(0, color="#667085", linestyle="--", linewidth=.9)
        ax.set_title("Selected-Expiry Fixed-Anchor Call and Put Skew: One Segment per Holding Period",
                     fontsize=13, fontweight="bold")
        ax.set_xlabel("Trade Date")
        ax.set_ylabel("Fixed-anchor half skew")
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.grid(color="#d9e0e8", linewidth=.7, alpha=.8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.legend(frameon=True, title="Factor")
        fig.autofmt_xdate(); fig.tight_layout()
        fig.savefig(csv_path.parent / "selected_expiry_call_put_skew_segments.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        count += 1
    return count


def render_attribution_titles() -> int:
    """Regenerate only the all-component attribution figures with revised titles."""
    base = ROOT / f"06_skew_strategy_{TAG}"
    components = [
        "DELTA_PNL", "GAMMA_PNL", "ATMVOL_PNL", "CALL_SKEW_PNL", "PUT_SKEW_PNL",
        "THETA_PNL", "ATMVOL_VANNA_PNL", "ATMVOL_VOLGA_PNL",
    ]
    count = 0
    for attribution_path in sorted(base.glob("expiry_*/traditional_taylor_attribution.csv")):
        expiry_code = attribution_path.parent.name.removeprefix("expiry_")
        attribution = pd.read_csv(attribution_path, parse_dates=["date"])
        capital_path = attribution_path.parent / "total_margin_daily.csv"
        capital = pd.read_csv(capital_path, parse_dates=["date"]) if capital_path.exists() else pd.DataFrame()
        figure_dir = attribution_path.parent / "figures" / "traditional_taylor"
        # Compact canvas for left-side placement in a 16:9 slide.
        fig, ax = plt.subplots(figsize=(11, 7))
        for component in components:
            ax.plot(attribution.date, attribution[component].cumsum(), label=component,
                    linewidth=2.3 if component in {"CALL_SKEW_PNL", "PUT_SKEW_PNL"} else 1.2)
        for column, label, style, color, width in [
            ("MODEL_RESIDUAL", "MODEL RESIDUAL", "--", "black", 2),
            ("MARKET_NOISE", "MARKET NOISE", ":", "#c0392b", 1.7),
            ("TOTAL_RESIDUAL", "TOTAL RESIDUAL", "-.", "#8e44ad", 1.8),
            ("FEE_PNL", "FEE PNL", ":", "#795548", 1.5),
            ("MODEL_PNL", "MODEL PNL", "-", "#34495e", 2.6),
            ("MARKET_PNL", "MARKET PNL", "-", "#1565c0", 2.6),
            ("ACTUAL_PNL_AFTER_FEES", "ACTUAL PNL AFTER FEES", "-", "black", 3),
        ]:
            ax.plot(attribution.date, attribution[column].cumsum(), label=label,
                    linestyle=style, color=color, linewidth=width)
        ax.axhline(0, color="#667085", linestyle="--", linewidth=.8)
        ax.set_title(f"Cumulative PnL Attribution ({expiry_code} Expiry)")
        ax.set_xlabel("Date"); ax.set_ylabel("Cumulative PnL"); ax.grid(alpha=.3)
        handles, labels = ax.get_legend_handles_labels()
        if not capital.empty:
            capital = capital.sort_values("date")
            capital_axis = ax.twinx()
            shadow = capital_axis.fill_between(capital.date, 0.0, capital.TOTAL_CAPITAL_OCCUPIED.astype(float),
                                                color="#90a4ae", alpha=.22, label="CAPITAL OCCUPIED", zorder=0)
            capital_axis.set_ylabel("Capital Occupied"); capital_axis.grid(False)
            handles.append(shadow); labels.append("CAPITAL OCCUPIED")
        ax.legend(handles, labels, ncol=3, fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        fig.autofmt_xdate(); fig.tight_layout()
        fig.savefig(figure_dir / "traditional_taylor_cumulative_attribution.png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        count += 1
    return count


def export_capital_return_summary_cn() -> Path:
    """Export the current capital summary with Chinese headings and annualized opening return."""
    path = ROOT / f"06_skew_strategy_{TAG}" / "capital_return_summary.csv"
    summary = pd.read_csv(path)
    ordered_columns = [
        "到期月份", "回测起始日", "回测结束日", "持有自然日数", "累计实际盈亏",
        "开仓占资日期", "开仓占资", "开仓占资收益率", "开仓占资年化收益率",
        "最大占资日期", "最大占资", "最大占资收益率", "最大占资年化收益率",
    ]
    if "到期月份" in summary.columns:
        if "最大占资年化收益率" not in summary.columns:
            maximum_return = pd.to_numeric(summary["最大占资收益率"], errors="coerce")
            summary["最大占资年化收益率"] = (1.0 + maximum_return) ** (365.0 / pd.to_numeric(summary["持有自然日数"], errors="coerce").clip(lower=1)) - 1.0
        def format_return(value):
            text = str(value)
            raw = float(text.rstrip("%")) / 100.0 if text.endswith("%") else float(value)
            return f"{raw:.2%}"
        return_columns = ["开仓占资收益率", "开仓占资年化收益率", "最大占资收益率", "最大占资年化收益率"]
        amount_columns = ["累计实际盈亏", "开仓占资", "最大占资"]
        for column in return_columns:
            summary[column] = summary[column].map(format_return)
        for column in amount_columns:
            summary[column] = pd.to_numeric(summary[column], errors="coerce").round(2)
        summary[ordered_columns].to_csv(path, index=False, encoding="utf-8-sig", float_format="%.2f")
        return path
    summary[["BACKTEST_START_DATE", "BACKTEST_END_DATE", "OPENING_CAPITAL_DATE", "MAX_CAPITAL_DATE"]] = summary[["BACKTEST_START_DATE", "BACKTEST_END_DATE", "OPENING_CAPITAL_DATE", "MAX_CAPITAL_DATE"]].apply(pd.to_datetime)
    holding_days = (summary["BACKTEST_END_DATE"] - summary["OPENING_CAPITAL_DATE"]).dt.days.clip(lower=1)
    opening_return = summary["CUMULATIVE_ACTUAL_PNL"] / summary["OPENING_CAPITAL_OCCUPIED"]
    summary["HOLDING_CALENDAR_DAYS"] = holding_days
    summary["ANNUALIZED_OPENING_CAPITAL_RETURN"] = (1.0 + opening_return) ** (365.0 / holding_days) - 1.0
    maximum_return = summary["CUMULATIVE_ACTUAL_PNL"] / summary["MAX_CAPITAL_OCCUPIED"]
    summary["ANNUALIZED_MAX_CAPITAL_RETURN"] = (1.0 + maximum_return) ** (365.0 / holding_days) - 1.0
    summary = summary.rename(columns={
        "EXPIRY_CODE": "到期月份", "BACKTEST_START_DATE": "回测起始日", "BACKTEST_END_DATE": "回测结束日",
        "HOLDING_CALENDAR_DAYS": "持有自然日数", "CUMULATIVE_ACTUAL_PNL": "累计实际盈亏",
        "OPENING_CAPITAL_DATE": "开仓占资日期", "OPENING_CAPITAL_OCCUPIED": "开仓占资",
        "OPENING_CAPITAL_RETURN": "开仓占资收益率", "ANNUALIZED_OPENING_CAPITAL_RETURN": "开仓占资年化收益率",
        "MAX_CAPITAL_DATE": "最大占资日期", "MAX_CAPITAL_OCCUPIED": "最大占资", "MAX_CAPITAL_RETURN": "最大占资收益率", "ANNUALIZED_MAX_CAPITAL_RETURN": "最大占资年化收益率",
    })
    summary = summary[ordered_columns]
    summary.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    return path


if __name__ == "__main__":
    print(f"05 updated charts: {render_05()}")
    print(f"06 updated charts: {render_06()}")
    print(f"06 updated attribution titles: {render_attribution_titles()}")
    print(f"Capital return summary: {export_capital_return_summary_cn()}")

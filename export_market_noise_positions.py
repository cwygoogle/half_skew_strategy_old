"""Export per-option market-noise diagnostics without altering positions.csv."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parent
MODEL_TAG = "QUADRATIC_HALF-SKEW_CURVATURE-WING"
STRATEGY_ROOT = PROJECT / "outputs" / f"06_skew_strategy_{MODEL_TAG}"
IV_PANEL_PATH = PROJECT / "outputs" / f"04_volatility_model_{MODEL_TAG}" / "option_iv_panel.csv"
PARAMETERS_PATH = PROJECT / "outputs" / f"04_volatility_model_{MODEL_TAG}" / "volatility_model_parameters.csv"
OPTION_MULTIPLIER = 100.0


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def model_price(row: pd.Series, parameter: pd.Series) -> float:
    """Black-76 price using the fitted quadratic IV at this option's k."""
    forward, strike, tau, rate = (
        float(row["FORWARD"]),
        float(row["STRIKE"]),
        float(row["TAU"]),
        float(row["RISK_FREE_RATE"]),
    )
    k = math.log(strike / forward)
    vol = max(
        float(parameter["a"])
        + float(parameter["b"]) * k
        + 0.5 * float(parameter["c"]) * k * k,
        1e-8,
    )
    discount = math.exp(-rate * tau)
    if tau <= 0.0:
        intrinsic = max(forward - strike, 0.0) if row["TYPE"] == "CALL" else max(strike - forward, 0.0)
        return discount * intrinsic
    d1 = (math.log(forward / strike) + 0.5 * vol * vol * tau) / (vol * math.sqrt(tau))
    d2 = d1 - vol * math.sqrt(tau)
    if row["TYPE"] == "CALL":
        return discount * (forward * normal_cdf(d1) - strike * normal_cdf(d2))
    return discount * (strike * normal_cdf(-d2) - forward * normal_cdf(-d1))


def export_expiry(expiry_code: str, options: pd.DataFrame, parameters: pd.DataFrame) -> None:
    expiry_dir = STRATEGY_ROOT / f"expiry_{expiry_code}"
    positions = pd.read_csv(expiry_dir / "positions.csv")
    pnl = pd.read_csv(expiry_dir / "daily_account_pnl.csv")
    positions["date"] = pd.to_datetime(positions["date"])
    pnl["date"] = pd.to_datetime(pnl["date"])

    option_positions = positions.loc[positions["asset_type"].eq("OPTION")].copy()
    diagnostics: list[dict[str, object]] = []
    for position_date, legs in option_positions.groupby("date", sort=True):
        future_dates = pnl.loc[pnl["date"].gt(position_date), "date"]
        if future_dates.empty:
            continue
        pnl_date = future_dates.min()
        for leg in legs.itertuples(index=False):
            old = options.loc[(options["TRADE_DT"].eq(position_date)) & (options["CODE"].eq(leg.code))].iloc[0]
            new = options.loc[(options["TRADE_DT"].eq(pnl_date)) & (options["CODE"].eq(leg.code))].iloc[0]
            old_parameter = parameters.loc[
                (parameters["TRADE_DT"].eq(position_date)) & (parameters["EXPIRY"].eq(old["EXPIRY"])
            )].iloc[0]
            new_parameter = parameters.loc[
                (parameters["TRADE_DT"].eq(pnl_date)) & (parameters["EXPIRY"].eq(new["EXPIRY"])
            )].iloc[0]
            previous_residual = float(old["PRICE"]) - model_price(old, old_parameter)
            current_residual = float(new["PRICE"]) - model_price(new, new_parameter)
            contribution = float(leg.qty) * OPTION_MULTIPLIER * (current_residual - previous_residual)
            record = leg._asdict()
            record.update(
                {
                    "PNL_DATE": pnl_date,
                    "PREVIOUS_DAY_MARKET_MINUS_MODEL": previous_residual,
                    "CURRENT_DAY_MARKET_MINUS_MODEL": current_residual,
                    "CURRENT_DAY_MARKET_NOISE_CONTRIBUTION": contribution,
                }
            )
            diagnostics.append(record)

    output = pd.DataFrame(diagnostics)
    output.to_csv(expiry_dir / "positions_with_market_noise_residuals.csv", index=False)


def main() -> None:
    options = pd.read_csv(IV_PANEL_PATH, encoding="utf-8-sig")
    parameters = pd.read_csv(PARAMETERS_PATH, encoding="utf-8-sig")
    options["TRADE_DT"] = pd.to_datetime(options["TRADE_DT"])
    parameters["TRADE_DT"] = pd.to_datetime(parameters["TRADE_DT"])
    parameters["EXPIRY"] = pd.to_datetime(parameters["EXPIRY"])
    for expiry_code in ("2607", "2612"):
        export_expiry(expiry_code, options, parameters)


if __name__ == "__main__":
    main()

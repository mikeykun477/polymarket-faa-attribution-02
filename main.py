#!/usr/bin/env python3
"""Forecast Polymarket's FAA outage attribution Yes prices, 4 hours ahead.

Entry for make.fun bounty polymarket-faa-attribution-02.

Method (per market, calibrated on the kit's six practice cases, which are
cut from Polymarket's "Next CEO of NVIDIA?" event, the same shape as the
final's FAA family):
  * The median is the last observed price (persistence). These prices are
    sticky step functions: most minutes do not move at all, so a random
    walk with the house spread (0.0025 * sqrt(h)) is far too wide.
  * The spread is calibrated per market from the standard deviation of its
    one-minute price changes over the last 120 minutes, floored at 0.0006
    and capped at 0.008 per minute before a 0.7 scale is applied
    (effective floor 0.00042, effective cap 0.0056 per minute).
  * The spread grows like h ** 0.4, not sqrt(h): realised moves over 4h
    are sub-diffusive (prices mean-revert / stay put), so the house's
    sqrt(h) growth overstates long-horizon uncertainty.
  * Quantiles use Student-t(3) levels instead of normal ones: realised
    moves are heavy-tailed, so the outer quantiles sit wider relative to
    the centre than a normal spread would put them, while the inner
    quantiles stay tight.
  * No drift: recent-trend drift was tested on the practice cases and
    hurts badly (mean-reverting step prices punish chasing the trend).
  * Quantiles are x + z_tau * spread, clamped to [0, 1], rounded to 6 dp.

Practice-case score (mean pinball loss, percentage points, scored against
Polymarket's public price history fetched for the practice windows):
  house baseline 0.372, this model 0.266 (the house's own recorded figure
  for the baseline is 0.364). The model is deterministic, stdlib only, no
  network, and runs in well under the 8s per-case cap.

Reads every <id>.in in $MAKEFUN_INPUT_DIR (else /input) and writes
<id>.out to $MAKEFUN_OUTPUT_DIR (else /output), one forecast per market,
240 rows of the five quantiles [0.05, 0.25, 0.5, 0.75, 0.95].
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
# Student-t(3) quantiles at the five levels, to 6 decimals.
Z = [-2.353363, -0.764892, 0.0, 0.764892, 2.353363]

SIGMA_WINDOW = 120      # minutes of one-minute changes used for calibration
SIGMA_FLOOR = 0.0006    # per-minute spread floor (quiet markets still move)
SIGMA_CAP = 0.008       # per-minute spread cap (a jumpy market stays sane)
SIGMA_SCALE = 0.7       # shrinkage on the calibrated spread
SPREAD_EXPONENT = 0.4   # sub-diffusive spread growth: sigma * h ** 0.4


def price6(x):
    """Clamp x to [0, 1] and round to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)), 6) + 0.0


def calibrate_sigma(prices):
    """Per-minute spread from the last SIGMA_WINDOW one-minute changes."""
    n = len(prices)
    if n < 2:
        return SIGMA_FLOOR
    start = max(0, n - SIGMA_WINDOW - 1)
    diffs = [prices[i + 1] - prices[i] for i in range(start, n - 1)]
    if not diffs:
        return SIGMA_FLOOR
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
    sigma = math.sqrt(var)
    # Floor/cap first, then scale: the tuned effective floor is 0.00042
    # and the effective cap 0.0056 per minute.
    return min(SIGMA_CAP, max(SIGMA_FLOOR, sigma)) * SIGMA_SCALE


def forecast(market, horizon):
    """240 rows (one per minute ahead) of the five quantiles for one market."""
    prices = market["prices"]
    if not prices:
        raise ValueError("market %s has no prices" % market["id"])
    x = prices[-1]
    sigma = calibrate_sigma(prices)
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * (h ** SPREAD_EXPONENT)
        rows.append([price6(x + z * spread) for z in Z])
    return rows


def main():
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    inputs = sorted(Path(INPUT_DIR).glob("*.in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as f:
            case = json.load(f)
        if case["quantiles"] != QUANTILES:
            raise ValueError(
                "%s asks for quantiles %s, not %s"
                % (path.name, case["quantiles"], QUANTILES)
            )
        horizon = case["horizon_minutes"]
        forecasts = [
            {"id": m["id"], "q": forecast(m, horizon)} for m in case["markets"]
        ]
        out_path = out_dir / (case_id + ".out")
        with out_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()

# FAA outage attribution forecaster

Entry for make.fun bounty **polymarket-faa-attribution-02** ($250):
forecast Polymarket's FAA outage attribution Yes prices minute by minute,
4 hours ahead, as five quantiles per market per minute.

## Method

Per market, calibrated on the kit's six practice cases (cut from
Polymarket's "Next CEO of NVIDIA?" event, the same shape as the final's
FAA family):

- **Median = last observed price (persistence).** These prices are sticky
  step functions: most minutes do not move at all.
- **Spread calibrated per market** from the standard deviation of its
  one-minute price changes over the last 120 minutes, floored at 0.0006
  and capped at 0.008 per minute before a 0.7 scale is applied
  (effective floor 0.00042, effective cap 0.0056 per minute).
- **Spread grows like h^0.4**, not sqrt(h): realised moves over 4 hours
  are sub-diffusive, so the house's sqrt(h) growth overstates
  long-horizon uncertainty.
- **Student-t(3) quantile levels** instead of normal ones: realised moves
  are heavy-tailed, so the outer quantiles sit wider relative to the
  centre than a normal spread would put them.
- **No drift:** recent-trend drift was tested on the practice cases and
  hurts badly (mean-reverting step prices punish chasing the trend).

## Practice score

Mean pinball loss, percentage points, scored against Polymarket's public
price history for the practice windows:

| model | loss |
|---|---|
| house baseline | 0.372 |
| this model | **0.266** |

(The house's own recorded figure for the baseline is 0.364.)

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `<id>.in` in `$MAKEFUN_INPUT_DIR` (else `/input`) and writes
`<id>.out` to `$MAKEFUN_OUTPUT_DIR` (else `/output`): one forecast per
market, 240 rows of the five quantiles `[0.05, 0.25, 0.5, 0.75, 0.95]`.

Deterministic, Python 3.13 standard library only, no network, well under
the 8-second per-case cap.

## License

MIT — see `LICENSE`.

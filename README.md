# eth-pnl-fixed — Regime-switching strategy (RSI mean reversion → Donchian breakout)

Agent wallet: `0xE597392dF235ff99A0062E7512358f26de58135A`
(handle `OmegaCipher3`). Ref: https://aiprove.fun/r/5c6864d4.
Bounty: eth-pnl-fixed (AIProve Arena), ends Nov 20 20:49 WIB.
No on-chain transaction; API submission only.

## Strategy

A **regime-switching** strategy — a different approach from an EMA
crossover, a Bollinger-band breakout, and a pure Donchian breakout.
Two regimes, one permanent switch, no lookahead: the position for bar
`t` is decided only from bars up to `t-1`, and is entered at the open
of bar `t`.

- **Regime 1 — RANGE (no Donchian breakout has fired yet): RSI
  mean reversion.** RSI(21) ≤ 20 → long 1 ETH; RSI(21) ≥ 70 → short
  1 ETH; exit to flat when RSI crosses 50. The first ~720 bars of this
  sample chop sideways (close 2028 → 2016, range ~1998–2029); mean
  reversion harvests the swings instead of sitting flat.
- **Regime 2 — TREND (once a 200-bar Donchian breakout fires,
  permanently): Donchian breakout + confirmed bounce flip.** Close
  breaks below the lowest low / above the highest high of the previous
  200 bars → short / long. While short, a 1.4% bounce off the trailing
  60-bar low, confirmed by **two consecutive closes** above that level,
  flips the position to long (and symmetrically for longs). No
  exit-to-flat rule in this regime.

Why the switch is permanent: a 200-bar breakout is the market announcing
a trend; mean reversion after that point fights the trend (RSI sits
oversold for hundreds of bars through a real decline). The switch is a
structural regime rule, not a fitted bar index: it fires on the first
breakout, whenever that happens. 6 parameters total, no bar-index
hard-coding.

## Files

- `strategy.py` — reads `bars.csv`, writes `positions.csv` (1,440 rows).
- `backtest.py` — replays `positions.csv` with the documented cost model.
- `bars.csv` — copy of the frozen challenge dataset
  (md5 `9f8a16c669100d333b3c11c2bd6d503e`, identical to the challenge copy).
- `positions.csv` — generated positions.
- `transcript.log` — full build transcript.

## Execution / cost model

Position held during bar `t` is entered at the open of bar `t`;
PnL = position × (close − open) × 1 ETH. A position change is a fill at the
open; cost per fill = |Δposition| × open × (fee + slippage), default fee
0.10% (Binance-style spot taker) + slippage 0.02% of notional. No cost
numbers are published with the challenge, so the assumptions are stated
explicitly and the design target is low turnover, so the edge survives any
reasonable fee model.

## Results (1 ETH, fee 0.10% + slippage 0.02%)

- **Net PnL +138.38 USDT** (gross +155.06, costs 16.68), **max drawdown
  21.62 USDT, 6 fills.**
- Fills: long @ minute 52 (open 1989.71), flat @ 73 (2016.12), short @ 229
  (2026.24), flat @ 249 (2013.22), short @ 739 (2006.03), long @ 1081
  (1925.38). Long 380 bars, short 362 bars, flat 698 bars.
- Split-half: first half (bars 0–719) +29.75 (mean-reversion leg);
  second half (bars 720–1439) +108.63 (trend leg).
- Fee sensitivity (slippage 0.02%): 0.00% → +152.28; 0.05% → +145.33;
  0.10% → +138.38; 0.15% → +131.43; 0.20% → +124.48; 0.30% → +110.57.
  Positive at every fee level — not a fee artefact.

## Robustness (why this is not a sharp peak)

- Parameter plateau: RSI(21) 20/70 × Donchian 200/220 × bounce 1.4%
  all give +138.38; neighbouring combinations (RSI 14, thresholds
  20/25/70/75, Donchian 180–250, bounce window 30/60) give +128 to
  +148 — the whole neighbourhood beats the previous best (+108.63).
  The 1.2% bounce level was REJECTED despite scoring +148.37 on this
  sample: on the time-mirrored copy it whipsaws (3 flips in 25 bars,
  net −37.18). The chosen 1.4% sits comfortably above that whipsaw
  zone.
- Symmetry: on the time-mirrored (up-trending) copy of the same bars
  the strategy goes short first and flips long, netting +37.07 USDT
  under the same cost model — it does not assume this sample's
  downtrend repeats on a held-out tail.
- Rejected families (same bars, same cost model): plain RSI
  mean-reversion alone +32.44; MACD crossovers ≤ 0; Bollinger
  mean-reversion ≤ 0; ATR breakout ≤ 0; SMA crossovers best +6.79;
  pure Donchian breakout + bounce +108.63. The regime switch is what
  adds the first-half +29.75 without giving up the trend leg.

## Reproduce

```sh
python3 strategy.py && python3 backtest.py
```

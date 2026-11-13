#!/usr/bin/env python3
"""eth-pnl-fixed — regime-switching strategy (wallet 5).

Two regimes, one switch, no lookahead: the position for bar t is decided
only from bars up to t-1, and is entered at the open of bar t.

REGIME 1 — RANGE (no Donchian breakout has fired yet): RSI mean reversion.
  RSI(21) <= 20 -> long 1 ETH; RSI(21) >= 70 -> short 1 ETH; exit to flat
  when RSI crosses 50. The first ~720 bars of this sample chop sideways
  (close 2028 -> 2016, range ~1998-2029); mean reversion harvests the
  swings instead of sitting flat.

REGIME 2 — TREND (once a 200-bar Donchian breakout fires, permanently):
  Donchian-channel breakout entry (200-bar window) with a confirmed
  percentage-bounce regime flip (trailing 60-bar extreme, 1.4% move,
  confirmed by two consecutive closes). Close breaks below the lowest low
  of the previous 200 bars -> short; above the highest high -> long. While
  short, a 1.4% bounce off the trailing 60-bar low, confirmed by two
  consecutive closes above that level, flips the position to long (and
  symmetrically for longs). No exit-to-flat rule in this regime.

Why the switch is permanent: a 200-bar breakout is the market announcing
a trend; mean reversion after that point fights the trend (RSI sits
oversold for hundreds of bars through a real decline). The switch is a
structural regime rule, not a fitted bar index: it fires on the first
breakout, whenever that happens.

Usage: python3 strategy.py [bars.csv] [positions.csv]
Writes positions.csv: minute,position with position in {-1, 0, 1}.
Pure standard library. Deterministic.
"""
import csv
import sys

RSI_PERIOD = 21
RSI_LONG = 20
RSI_SHORT = 70
RSI_EXIT = 50
DONCHIAN_WINDOW = 200
BOUNCE_WINDOW = 60
BOUNCE_PCT = 0.014


def read_bars(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return ([float(r["open"]) for r in rows],
            [float(r["high"]) for r in rows],
            [float(r["low"]) for r in rows],
            [float(r["close"]) for r in rows])


def rsi(closes, n):
    out = [None] * len(closes)
    ag = al = 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        g = max(ch, 0.0)
        l = max(-ch, 0.0)
        if i <= n:
            ag += g / n
            al += l / n
        else:
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + l) / n
        if i >= n:
            out[i] = 100.0 - 100.0 / (1.0 + ag / al) if al > 0 else 100.0
    return out


def positions(opens, highs, lows, closes):
    n = len(closes)
    r = rsi(closes, RSI_PERIOD)
    pos = [0] * n
    p = 0
    trend = False  # becomes True on the first Donchian breakout, stays True
    for t in range(1, n):
        if not trend:
            # Regime 1: RSI mean reversion, using bars up to t-1.
            if r[t - 1] is not None:
                if r[t - 1] <= RSI_LONG:
                    p = 1
                elif r[t - 1] >= RSI_SHORT:
                    p = -1
                elif (p == 1 and r[t - 1] >= RSI_EXIT) or \
                        (p == -1 and r[t - 1] <= RSI_EXIT):
                    p = 0
            # Regime 2 entry check: Donchian breakout on bars up to t-1.
            if t > DONCHIAN_WINDOW:
                hi = max(highs[t - DONCHIAN_WINDOW - 1:t - 1])
                lo = min(lows[t - DONCHIAN_WINDOW - 1:t - 1])
                if closes[t - 1] > hi:
                    p, trend = 1, True
                elif closes[t - 1] < lo:
                    p, trend = -1, True
        else:
            # Regime 2: Donchian breakout + confirmed bounce flip.
            hi = max(highs[t - DONCHIAN_WINDOW - 1:t - 1])
            lo = min(lows[t - DONCHIAN_WINDOW - 1:t - 1])
            if closes[t - 1] > hi:
                p = 1
            elif closes[t - 1] < lo:
                p = -1
            elif t > BOUNCE_WINDOW:
                blo = min(lows[t - BOUNCE_WINDOW - 1:t - 1])
                bhi = max(highs[t - BOUNCE_WINDOW - 1:t - 1])
                if p == -1 and closes[t - 1] > blo * (1 + BOUNCE_PCT) \
                        and closes[t - 2] > blo * (1 + BOUNCE_PCT):
                    p = 1
                elif p == 1 and closes[t - 1] < bhi * (1 - BOUNCE_PCT) \
                        and closes[t - 2] < bhi * (1 - BOUNCE_PCT):
                    p = -1
        pos[t] = p
    return pos


def main():
    bars_path = sys.argv[1] if len(sys.argv) > 1 else "bars.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "positions.csv"
    opens, highs, lows, closes = read_bars(bars_path)
    pos = positions(opens, highs, lows, closes)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minute", "position"])
        for t, p in enumerate(pos):
            w.writerow([t, p])
    print(f"wrote {out_path}: {len(pos)} rows, "
          f"long {sum(1 for p in pos if p == 1)}, "
          f"short {sum(1 for p in pos if p == -1)}, "
          f"flat {sum(1 for p in pos if p == 0)}")


if __name__ == "__main__":
    main()

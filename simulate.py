#!/usr/bin/env python3
"""Percentile Pocket: simulate a year of income/spending many times. Standard library only."""
import argparse, html, json, math, random, sys
from pathlib import Path

PERCENTILES = [10, 25, 50, 75, 90]
BINS = 40


class ConfigError(Exception):
    pass


# ---------- validation ----------
def num(v, field):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ConfigError(f"{field}: must be a number")
    return float(v)


def pos_int(v, field):
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ConfigError(f"{field}: must be an integer >= 1")
    return v


NEEDS = {"fixed": ["amount"], "normal": ["mean", "sd"],
         "uniform": ["low", "high"], "triangular": ["low", "high", "mode"]}


def validate_amount(v, field):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {"distribution": "fixed", "amount": num(v, field)}
    if not isinstance(v, dict):
        raise ConfigError(f"{field}: must be a number or a distribution object")
    d = v.get("distribution")
    if d not in NEEDS:
        raise ConfigError(f"{field}: unknown distribution {d!r}")
    spec = {"distribution": d}
    for k in NEEDS[d]:
        if k not in v:
            raise ConfigError(f"{field}: missing '{k}' for {d}")
        spec[k] = num(v[k], f"{field}.{k}")
    if d == "normal" and spec["sd"] <= 0:
        raise ConfigError(f"{field}.sd: must be greater than 0")
    if d in ("uniform", "triangular") and spec["low"] >= spec["high"]:
        raise ConfigError(f"{field}: low must be less than high")
    if d == "triangular" and not spec["low"] <= spec["mode"] <= spec["high"]:
        raise ConfigError(f"{field}.mode: must be between low and high")
    for k in ("minimum", "maximum"):
        if k in v:
            spec[k] = num(v[k], f"{field}.{k}")
    return spec


def validate_config(c):
    if not isinstance(c, dict):
        raise ConfigError("config must be a JSON object")
    for k in ("months", "runs", "starting_balance", "monthly_income",
              "monthly_fixed_expenses", "monthly_variable_expenses"):
        if k not in c:
            raise ConfigError(f"missing required field '{k}'")
    out = {
        "name": str(c.get("name", "unnamed scenario")),
        "currency": str(c.get("currency", "USD")),
        "months": pos_int(c["months"], "months"),
        "runs": pos_int(c["runs"], "runs"),
        "seed": c.get("seed", 0),
        "starting_balance": num(c["starting_balance"], "starting_balance"),
        "income": validate_amount(c["monthly_income"], "monthly_income"),
        "fixed": validate_amount(c["monthly_fixed_expenses"], "monthly_fixed_expenses"),
        "variable": validate_amount(c["monthly_variable_expenses"], "monthly_variable_expenses"),
        "one_time": [],
    }
    if isinstance(out["seed"], bool) or not isinstance(out["seed"], int):
        raise ConfigError("seed: must be an integer")
    items = c.get("one_time_expenses", [])
    if not isinstance(items, list):
        raise ConfigError("one_time_expenses: must be a list")
    for i, it in enumerate(items):
        f = f"one_time_expenses[{i}]"
        if not isinstance(it, dict) or "month" not in it or "amount" not in it:
            raise ConfigError(f"{f}: needs 'month' and 'amount'")
        m = pos_int(it["month"], f"{f}.month")
        if m > out["months"]:
            raise ConfigError(f"{f}.month: outside the {out['months']}-month period")
        out["one_time"].append({"month": m, "amount": num(it["amount"], f"{f}.amount"),
                                "label": str(it.get("label", ""))})
    return out


def load_config(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path} is not valid JSON: {e}")


# ---------- simulation ----------
def sample(rng, s):
    d = s["distribution"]
    if d == "fixed":
        x = s["amount"]
    elif d == "normal":
        x = rng.gauss(s["mean"], s["sd"])
    elif d == "uniform":
        x = rng.uniform(s["low"], s["high"])
    else:
        x = rng.triangular(s["low"], s["high"], s["mode"])
    if "minimum" in s:
        x = max(x, s["minimum"])
    if "maximum" in s:
        x = min(x, s["maximum"])
    return x


def percentile(sorted_vals, p):
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def simulate(cfg):
    rng = random.Random(cfg["seed"])
    one_time = {}
    for it in cfg["one_time"]:
        one_time[it["month"]] = one_time.get(it["month"], 0) + it["amount"]
    months, runs = cfg["months"], cfg["runs"]
    per_month = [[] for _ in range(months)]
    ends, never_neg = [], 0
    for _ in range(runs):
        bal, dipped = cfg["starting_balance"], False
        for m in range(1, months + 1):
            bal += sample(rng, cfg["income"]) - sample(rng, cfg["fixed"]) \
                   - sample(rng, cfg["variable"]) - one_time.get(m, 0)
            per_month[m - 1].append(bal)
            if bal < 0:
                dipped = True
        ends.append(bal)
        never_neg += (not dipped)
    s_ends = sorted(ends)
    bands = [{f"p{p}": percentile(sorted(col), p) for p in PERCENTILES} for col in per_month]
    lo, hi = s_ends[0], s_ends[-1]
    width = (hi - lo) / BINS or 1.0
    counts = [0] * BINS
    for v in ends:
        counts[min(int((v - lo) / width), BINS - 1)] += 1
    return {
        "name": cfg["name"], "currency": cfg["currency"], "runs": runs, "months": months,
        "seed": cfg["seed"], "starting_balance": cfg["starting_balance"],
        "percentiles": {f"p{p}": percentile(s_ends, p) for p in PERCENTILES},
        "mean": sum(ends) / runs, "min": lo, "max": hi,
        "ended_above_zero": sum(v > 0 for v in ends),
        "never_below_zero": never_neg,
        "monthly_bands": bands,
        "histogram": {"low": lo, "bin_width": width, "counts": counts},
    }


# ---------- report ----------
def money(v, cur):
    return f"{cur} {v:,.0f}"


def svg_histogram(r, W=720, H=260):
    h = r["histogram"]; c = h["counts"]; mx = max(c)
    pad, bw = 30, (W - 60) / len(c)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Distribution of ending balances">']
    for i, n in enumerate(c):
        bh = (H - 2 * pad) * n / mx
        neg = h["low"] + (i + 1) * h["bin_width"] <= 0
        out.append(f'<rect x="{pad + i * bw:.1f}" y="{H - pad - bh:.1f}" width="{bw - 1:.1f}" '
                   f'height="{bh:.1f}" fill="{"#c0392b" if neg else "#2e86c1"}"/>')
    span = h["bin_width"] * len(c)
    if h["low"] < 0 < h["low"] + span:
        x = pad + (-h["low"] / span) * (W - 60)
        out.append(f'<line x1="{x:.1f}" y1="{pad}" x2="{x:.1f}" y2="{H - pad}" stroke="#333" stroke-dasharray="4"/>')
    out.append(f'<text x="{pad}" y="{H - 8}" font-size="11">{r["min"]:,.0f}</text>')
    out.append(f'<text x="{W - pad}" y="{H - 8}" font-size="11" text-anchor="end">{r["max"]:,.0f}</text></svg>')
    return "".join(out)


def svg_bands(r, W=720, H=300):
    start = {f"p{p}": r["starting_balance"] for p in PERCENTILES}
    rows = [start] + r["monthly_bands"]
    allv = [v for row in rows for v in row.values()]
    lo, hi = min(allv + [0]), max(allv + [0])
    pad = 30
    X = lambda i: pad + i * (W - 2 * pad) / (len(rows) - 1 or 1)
    Y = lambda v: H - pad - (v - lo) / ((hi - lo) or 1) * (H - 2 * pad)

    def poly(a, b, color):
        pts = [f"{X(i):.1f},{Y(row[a]):.1f}" for i, row in enumerate(rows)] + \
              [f"{X(i):.1f},{Y(row[b]):.1f}" for i, row in reversed(list(enumerate(rows)))]
        return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'

    line = lambda k, col: '<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (
        col, " ".join(f"{X(i):.1f},{Y(row[k]):.1f}" for i, row in enumerate(rows)))
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Balance bands by month">'
            + poly("p10", "p90", "#d6eaf8") + poly("p25", "p75", "#85c1e9") + line("p50", "#1b4f72")
            + f'<line x1="{pad}" y1="{Y(0):.1f}" x2="{W - pad}" y2="{Y(0):.1f}" stroke="#333" stroke-dasharray="4"/>'
            + f'<text x="{pad}" y="{H - 8}" font-size="11">month 0</text>'
            + f'<text x="{W - pad}" y="{H - 8}" font-size="11" text-anchor="end">month {len(rows) - 1}</text></svg>')


def render_report(r):
    cur, n = r["currency"], r["runs"]
    rows = "".join(f"<tr><td>{k}</td><td>{money(v, cur)}</td></tr>" for k, v in r["percentiles"].items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(r['name'])}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:780px;margin:2rem auto;padding:0 1rem;color:#222}}
svg{{width:100%;height:auto;background:#fafafa;border:1px solid #ddd}}
td,th{{padding:.3rem .8rem;text-align:left;border-bottom:1px solid #eee}}.note{{background:#fff8e1;padding:1rem}}</style></head><body>
<h1>{html.escape(r['name'])}</h1>
<p>{n:,} runs of {r['months']} months, seed {r['seed']}. Starting balance {money(r['starting_balance'], cur)}.</p>
<h2>Ending balance</h2><table>{rows}<tr><td>mean</td><td>{money(r['mean'], cur)}</td></tr>
<tr><td>range</td><td>{money(r['min'], cur)} to {money(r['max'], cur)}</td></tr></table>
<p>Ended above zero: <b>{r['ended_above_zero']:,}</b> of {n:,} ({r['ended_above_zero'] / n:.1%} of simulated runs)<br>
Never below zero: <b>{r['never_below_zero']:,}</b> of {n:,} ({r['never_below_zero'] / n:.1%} of simulated runs)</p>
<h2>Where the futures cluster</h2>{svg_histogram(r)}
<h2>Balance bands by month (p10-p90 light, p25-p75 dark, median line)</h2>{svg_bands(r)}
<p class="note">Educational simulation of user-supplied assumptions, not financial advice and not a prediction.
Not modeled: taxes, inflation, investment returns, debt interest, income/expense correlation, currency changes,
unexpected events beyond configured one-time items, behavioral changes, real market data.</p></body></html>"""


def summary(r):
    cur, n = r["currency"], r["runs"]
    L = [r["name"], f"  {n:,} runs of {r['months']} months, seed {r['seed']}",
         f"  Starting balance: {money(r['starting_balance'], cur)}", "", "  Ending balance"]
    for k, v in r["percentiles"].items():
        L.append(f"    {k:<8}{money(v, cur):>16}")
    L += [f"    {'mean':<8}{money(r['mean'], cur):>16}",
          f"    range   {money(r['min'], cur)} to {money(r['max'], cur)}", "",
          f"  Ended above zero: {r['ended_above_zero']:>7,} of {n:,} ({r['ended_above_zero'] / n:.1%} of simulated runs)",
          f"  Never below zero: {r['never_below_zero']:>7,} of {n:,} ({r['never_below_zero'] / n:.1%} of simulated runs)", "",
          "  These are shares of simulated runs under your assumptions,",
          "  not probabilities about your actual year."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Simulate a year of income and spending many times.")
    ap.add_argument("config", help="path to JSON config")
    ap.add_argument("--output", default="output", help="output directory")
    ap.add_argument("--runs", type=int, help="override runs")
    ap.add_argument("--seed", type=int, help="override seed")
    a = ap.parse_args(argv)
    try:
        raw = load_config(a.config)
        if a.runs is not None and isinstance(raw, dict):
            raw["runs"] = a.runs
        if a.seed is not None and isinstance(raw, dict):
            raw["seed"] = a.seed
        cfg = validate_config(raw)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2
    res = simulate(cfg)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    (out / "report.html").write_text(render_report(res), encoding="utf-8")
    print(summary(res))
    print(f"\n  Wrote {out / 'results.json'}\n  Wrote {out / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

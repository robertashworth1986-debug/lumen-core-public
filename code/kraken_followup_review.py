import json
import statistics
import urllib.request

# Entry snapshot from the previous scan output.
ENTRY = {
    "RIVERUSD": 6.5590,
    "TRUMPUSD": 2.6030,
    "MINAUSD": 0.0637,
    "APEUSD": 0.1432,
    "ONDOUSD": 0.26799,
    "SUIUSD": 0.9457,
    "WIFUSD": 0.1787,
}


def get_ticker_for_pairs(pairs):
    url = "https://api.kraken.com/0/public/Ticker?pair=" + ",".join(pairs)
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data["result"]


def map_current_prices(pairs):
    result = get_ticker_for_pairs(pairs)
    current = {}

    for k, v in result.items():
        px = float(v["c"][0])
        matched = None
        for p in pairs:
            if p in k:
                matched = p
                break
            if p.replace("USD", "") in k and ("USD" in k or "ZUSD" in k):
                matched = p
                break
        if matched:
            current[matched] = px

    for p in pairs:
        if p in current:
            continue
        with urllib.request.urlopen(f"https://api.kraken.com/0/public/Ticker?pair={p}", timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
        key = next(iter(d["result"].keys()))
        current[p] = float(d["result"][key]["c"][0])

    return current


def main():
    pairs = list(ENTRY.keys())
    current = map_current_prices(pairs)

    rows = []
    for p, e in ENTRY.items():
        c = current[p]
        ret = (c / e) - 1.0
        rows.append((p, e, c, ret))

    rows.sort(key=lambda x: x[3], reverse=True)

    print("FOLLOWUP SNAPSHOT (entry -> now)")
    print("pair,entry,now,return_pct")
    for p, e, c, r in rows:
        print(f"{p},{e:.8f},{c:.8f},{r*100:.2f}")

    capital = 500.0
    allocs = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

    print("\nPNL TABLE PER SYMBOL (allocated X% of $500)")
    for p, e, c, r in rows:
        print(f"-- {p} --")
        for a in allocs:
            stake = capital * a
            pnl = stake * r
            print(f"alloc={int(a*100)}% stake=${stake:.2f} pnl=${pnl:.2f} final=${stake+pnl:.2f}")

    basket_ret = statistics.mean([r for _, _, _, r in rows])
    best_ret = rows[0][3]
    med_ret = statistics.median([r for _, _, _, r in rows])

    print("\nSTRATEGY COMPARISON ($500 notional)")
    for name, r in [
        ("S1 equal-weight basket (7 names)", basket_ret),
        ("S2 best single name (hindsight upper bound)", best_ret),
        ("S3 median single name (more typical)", med_ret),
    ]:
        pnl = capital * r
        print(f"{name}: return={r*100:.2f}% pnl=${pnl:.2f} final=${capital+pnl:.2f}")

    print("S0 missed trade: return=0.00% pnl=$0.00 final=$500.00")


if __name__ == "__main__":
    main()

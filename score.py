"""Rule hints for verdicts: mark each scanned trait change as converging or diverging.

Run after the scans and before writing data/verdicts.json:  python3 score.py
Output: data/rule_hints.json (not used by the site; a starting point for verdicts).

The rule: a trait change converges if, after it, more catalog wallets (other than this one)
share the wallet's value than before. It diverges if fewer do. A value no other wallet uses
counts as zero, so introducing a brand-new behavior is diverging. A few traits have a
recommended value that wins over the head count (see RECOMMENDED).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Scan "wallet" names that map to a catalog row with a different name.
CATALOG_NAME = {"BDK": "ldk-node"}

# Values that are better for privacy than the head count suggests. Moving to one of these
# counts as converging, and moving away from one counts as diverging.
RECOMMENDED = {
    "nlocktime": ["anti-fee-sniping (±100 blocks)", "anti-fee-sniping", "exact tip"],
    "input_ordering": ["shuffle"],
    "change_position": ["random"],
    "low_r": ["yes"],
    "nsequence": ["0xFFFFFFFD (RBF)"],
}


def norm(text):
    return " ".join(str(text).lower().replace("_", " ").split())


def others_sharing(dist, key, value, wallet):
    """Number of catalog wallets other than `wallet` whose value for `key` matches `value`."""
    if key not in dist or value is None:
        return 0
    v = norm(value)
    for text, wallets in dist[key]["values"].items():
        t = norm(text)
        if v == t or (len(v) > 3 and (v in t or t in v)):
            return len([w for w in wallets if w != wallet])
    return 0


def is_recommended(key, value):
    v = norm(value)
    return any(norm(r) == v for r in RECOMMENDED.get(key, []))


def score_trait(dist, wallet, t):
    key = t.get("key", "")
    before, after = t.get("before"), t.get("after")
    b = others_sharing(dist, key, before, wallet)
    a = others_sharing(dist, key, after, wallet)
    rec_b, rec_a = is_recommended(key, before), is_recommended(key, after)
    if rec_a and not rec_b:
        direction = "converging"
    elif rec_b and not rec_a:
        direction = "diverging"
    elif a > b:
        direction = "converging"
    elif a < b:
        direction = "diverging"
    else:
        direction = "neutral"
    return {**t, "others_before": b, "others_after": a, "direction": direction,
            "known_trait": key in dist}


def overall(directions):
    d = set(directions) - {"neutral"}
    if not d:
        return "neutral"
    if len(d) == 1:
        return d.pop()
    return "mixed"


def main():
    dist = json.load(open(os.path.join(HERE, "data", "trait_distribution.json")))
    entries, seen = [], set()
    for path in sorted(glob.glob(os.path.join(HERE, "data", "scans", "*.json"))):
        try:
            items = json.load(open(path))
        except json.JSONDecodeError as e:
            print(f"skipping {path}: {e}", file=sys.stderr)
            continue
        for e in items:
            ident = (e.get("repo"), e.get("pr") or e.get("url"))
            if ident in seen:
                continue
            seen.add(ident)
            wallet = CATALOG_NAME.get(e.get("wallet"), e.get("wallet"))
            e["traits"] = [score_trait(dist, wallet, t) for t in e.get("traits", [])]
            e["direction"] = overall(t["direction"] for t in e["traits"])
            e["source_file"] = os.path.basename(path)
            entries.append(e)
    entries.sort(key=lambda e: e.get("date") or "", reverse=True)
    out = os.path.join(HERE, "data", "rule_hints.json")
    json.dump({"entries": entries}, open(out, "w"), indent=1, ensure_ascii=False)

    from collections import Counter
    print(f"{len(entries)} entries -> {out}")
    print("by direction:", dict(Counter(e["direction"] for e in entries)))
    print("by wallet:   ", dict(Counter(e["wallet"] for e in entries)))
    print("by state:    ", dict(Counter(e.get("state") for e in entries)))
    print("by confidence:", dict(Counter(e.get("confidence") for e in entries)))


if __name__ == "__main__":
    main()

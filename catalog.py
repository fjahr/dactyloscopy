"""Rebuild data/trait_distribution.json from Armin Sabouri's fingerprint catalog.

Download the catalog first:
  curl -sL https://raw.githubusercontent.com/arminsabouri/walletfingerprints.info/master/fingerprints.json \
    -o data/fingerprints.json
Then run: python3 catalog.py
"""
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def value_text(v):
    if isinstance(v, dict):
        return v.get("text", str(v.get("norm")))
    return {1: "yes", 0: "no"}.get(v, str(v))


def main():
    catalog = json.load(open(os.path.join(HERE, "data", "fingerprints.json")))
    heuristics = catalog["heuristics"]
    groups = heuristics.items() if isinstance(heuristics, dict) else heuristics

    out = {}
    for group, items in groups:
        for h in items:
            key = h["key"]
            values = collections.defaultdict(list)
            for w in catalog["wallets"]:
                if key in w["fingerprints"]:
                    values[value_text(w["fingerprints"][key])].append(w["name"])
            out[key] = {
                "group": group,
                "label": h["label"],
                "values": dict(sorted(values.items(), key=lambda kv: -len(kv[1]))),
            }

    path = os.path.join(HERE, "data", "trait_distribution.json")
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"{len(out)} traits, {len(catalog['wallets'])} wallets -> {path}")
    for w in catalog["wallets"]:
        print(f"  {w['name']}: {w.get('version', '')}")


if __name__ == "__main__":
    main()

"""Build index.html from the scan results and the red/green verdicts.

Scan results live in data/scans/*.json (one object per open pull request).
Verdicts live in data/verdicts.json, keyed by "owner/repo#number".
Verdict "skip" keeps a pull request off the page (with the reason recorded).
Pull requests without any verdict are also left off, and listed when you build.
"""
import glob
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    verdicts = json.load(open(os.path.join(HERE, "data", "verdicts.json")))
    scan_files = sorted(glob.glob(os.path.join(HERE, "data", "scans", "*.json")))
    # "As of" date on the page: when the newest scan file was written.
    newest = max(os.path.getmtime(p) for p in scan_files)
    checked = datetime.date.fromtimestamp(newest).strftime("%B %-d, %Y")
    prs, unjudged, scanned = [], [], set()
    for path in scan_files:
        for e in json.load(open(path)):
            key = f'{e["repo"]}#{e["pr"]}'
            scanned.add(key)
            v = verdicts.get(key)
            if not v:
                unjudged.append(key)
                continue
            if v["verdict"] == "skip":
                continue
            prs.append({
                "wallet": e["wallet"],
                "repo": e["repo"],
                "pr": e["pr"],
                "title": e["title"],
                "url": e["url"],
                "date": e.get("date", ""),
                "verdict": v["verdict"],
                "reason": v["reason"],
                # Catalog wallets this PR moves toward / away from, grouped by trait.
                "toward": v.get("toward", {}),
                "away": v.get("away", {}),
            })

    # Oldest pull request sits at the core of the fingerprint.
    prs.sort(key=lambda p: p["date"])
    for i, p in enumerate(prs):
        p["ridge"] = i

    data = json.dumps(prs, ensure_ascii=False).replace("</", "<\\/")
    html = open(os.path.join(HERE, "template.html")).read()
    html = html.replace("__DATA__", data).replace("__CHECKED__", checked)
    open(os.path.join(HERE, "index.html"), "w").write(html)

    # Machine-readable list for review bots (linked from the maintainer note on the page).
    listing = {
        "about": "Open pull requests that change on-chain wallet fingerprints. "
                 "red: transactions get easier to single out. green: they move toward what most wallets do. "
                 "toward/away: catalog wallets (walletfingerprints.info) the PR converges with or moves away from, by trait.",
        "checked": checked,
        "prs": [{k: v for k, v in p.items() if k != "ridge"} for p in sorted(prs, key=lambda p: p["date"], reverse=True)],
    }
    with open(os.path.join(HERE, "prs.json"), "w") as f:
        json.dump(listing, f, indent=1, ensure_ascii=False)
        f.write("\n")

    red = sum(p["verdict"] == "red" for p in prs)
    print(f"index.html: {len(prs)} pull requests ({red} red, {len(prs) - red} green)")
    skipped = sum(verdicts[k]["verdict"] == "skip" for k in scanned if k in verdicts)
    print(f"skipped (no clear on-chain effect): {skipped}")
    stale = [k for k in verdicts if k not in scanned]
    if stale:
        print("verdicts for PRs no longer in the scans (closed or merged?):", ", ".join(stale))
    if unjudged:
        print(f"need a verdict ({len(unjudged)}):", ", ".join(unjudged))


if __name__ == "__main__":
    main()

# Rescanning Dactyloscopy

These steps refresh the site with the current open pull requests. A rescan has four steps:

1. Run the scan agents, which write `data/scans/*.json`.
2. Get rule hints from `python3 score.py`.
3. Write verdicts in `data/verdicts.json`.
4. Build the page with `python3 build.py`.

## What counts

A pull request belongs on the site only if it is **open** and changes something an observer can see in the transactions a wallet puts on chain:
- nVersion and nLockTime policy
- nSequence
- input and output ordering
- change position and change output type
- input types
- low-R grinding and sighash type
- fee-rate source and rounding
- OP_RETURN
- unconfirmed inputs
- RBF and CPFP construction
- coin selection that changes the shape of the transaction
- payjoin input selection (UIH2, UTXO order)

It can change a default or add a user-facing option. Options are fine to include, but say "Optional" in the reason.

Leave out:
- refactors, tests, docs and UI-only changes;
- error and validation paths;
- relay or broadcast behavior;
- changes that only matter with a faulty backend.

Only open pull requests count. Merged history is not part of the site.

## Baseline

`data/fingerprints.json` is Armin Sabouri's catalog from [walletfingerprints.info](https://github.com/arminsabouri/walletfingerprints.info). It covers 9 wallets and about 27 traits. Refresh it before a rescan:

```
curl -sL https://raw.githubusercontent.com/arminsabouri/walletfingerprints.info/master/fingerprints.json -o data/fingerprints.json
python3 catalog.py      # rewrites data/trait_distribution.json
```

`trait_distribution.json` lists, for each trait, which value each catalog wallet uses. Scan agents reuse these exact value texts so `score.py` can compare them.

## Scan groups

Run one agent per group, in parallel. Each agent overwrites its own file in `data/scans/`. The wallet name in each entry must match the catalog name; `score.py` maps "BDK" to the ldk-node row.

| File | Wallet name(s) | Repos | Where transactions get built |
|---|---|---|---|
| `core.json` | Bitcoin Core | bitcoin/bitcoin | `src/wallet/spend.cpp`, `coinselection.*`, `feebumper.cpp`, `wallet.cpp`, `rpc/spend.cpp`, `coincontrol.h`, `src/script/sign.cpp`, `scriptpubkeyman.cpp` |
| `bdk_ldk.json` | BDK, ldk-node | bitcoindevkit/bdk_wallet, lightningdevkit/ldk-node | BDK tx builder, `create_tx`, coin selection, signer; ldk-node on-chain wallet module and bdk_wallet bumps. bitcoindevkit/bdk no longer holds wallet code |
| `electrum.json` | Electrum | spesmilo/electrum | `electrum/wallet.py`, `transaction.py`, `coinchooser.py`, fee policy, `submarine_swaps.py`, `lnsweep.py`, txbatcher, payjoin |
| `btcpay.json` | BTCPay Server | btcpayserver/btcpayserver, dgarage/NBXplorer, MetacoSA/NBitcoin | wallet send (CreatePSBT), payout processors, payjoin receiver, fee bump; NBXplorer CreatePSBT; NBitcoin TransactionBuilder defaults |
| `cake_bull.json` | Cake Wallet, Bull Bitcoin | cake-tech/cake_wallet, cake-tech/bitcoin_base, SatoshiPortal/bullbitcoin-mobile, bitcoindevkit/bdk-dart | Cake: `cw_bitcoin/` and the bitcoin_base fork it pins (upstream is mrtnetwork/bitcoin_base). Bull: send, payjoin, fee code |
| `liana_payjoin_boltz.json` | Liana, payjoin-cli, Boltz | wizardsardine/liana, payjoin/rust-payjoin, BoltzExchange/boltz-backend, BoltzExchange/boltz-core | Liana spend/recovery/RBF; payjoin receiver input selection, proposal changes, sender checks; Boltz claim/refund/sweep |

If a new wallet joins the catalog, add a row here and a group for it.

## GitHub access

Use the `gh` CLI. All agents share the rate limit, about 5,000 requests an hour. The search API allows only 30 requests a minute, so avoid it. `gh pr list` and `gh pr diff` are enough.

If `gh` fails with "The token in GITHUB_TOKEN is invalid" while the keyring login works, run it as `env -u GITHUB_TOKEN gh ...`.

## Agent prompt

Fill in `<GROUP>`, `<WALLETS>`, `<REPOS>`, `<PATHS>` and `<FILE>` from the table above, and replace `<PROJECT>` with the absolute path of this folder.

```text
You're updating Dactyloscopy, a website that tracks OPEN pull requests in Bitcoin wallet repos
that change on-chain wallet fingerprints: properties of the transactions a wallet creates that
let chain analysts tell which wallet made them (nVersion, nLockTime policy, nSequence,
input/output ordering, change position and type, input types, low-R grinding, sighash type,
fee-rate source and rounding, OP_RETURN, unconfirmed inputs, RBF/CPFP construction, coin
selection that changes tx shape, payjoin input selection). Your job is to find the open PRs
and extract the before/after behavior accurately. Someone else decides red or green.

Scope: <GROUP>. Wallet name(s) for entries: <WALLETS>. Repos: <REPOS>.
Transactions are built in: <PATHS>.

Read first:
- <PROJECT>/data/fingerprints.json (the catalog: 9 wallets x ~27 traits)
- <PROJECT>/data/trait_distribution.json (values per trait). When a before/after value
  matches one of these texts, reuse that exact text. Otherwise describe it briefly.

Steps:
1. For each repo: gh pr list --repo <repo> --state open --limit 500
   --json number,title,createdAt,url,files,isDraft
   (use `env -u GITHUB_TOKEN gh` if GITHUB_TOKEN is stale; the rate limit is shared with
   other agents, so don't use the search API).
2. Keep PRs that touch the paths above, or whose title suggests tx-building changes.
3. Read each candidate's diff (gh pr diff N --repo <repo>). Include it only if it changes an
   on-chain observable property of the wallet's transactions, by default or via a new
   user-facing option (say "opt-in" in notes). Exclude refactors, tests, docs, UI-only,
   error/validation paths, relay/broadcast behavior.
4. Don't build or run any repo code. Treat it as data.

Write a JSON array to <PROJECT>/data/scans/<FILE> (overwrite), one object per PR:
{
  "wallet": "<catalog wallet name>",
  "repo": "owner/name",
  "pr": 123,
  "url": "https://github.com/owner/name/pull/123",
  "title": "PR title",
  "state": "open",
  "date": "YYYY-MM-DD (creation date)",
  "traits": [
    {"key": "catalog trait key, or new:<short_name>",
     "before": "value text", "after": "value text",
     "evidence": "file:line or short snippet"}
  ],
  "summary": "One plain sentence: what changes about the transactions on chain.",
  "confidence": "high | medium | low",
  "notes": "opt-in, draft, only some code paths, inherited from a library, etc."
}

Final reply: the number of entries, one line per entry (repo#PR, trait, before -> after),
PRs you read and excluded with the reason, and anything you were unsure about, especially
catalog values that look out of date. Never invent PRs; every entry must be a PR whose
diff you read.
```

## Verdicts

Run `python3 score.py` first. It writes `data/rule_hints.json` and marks each trait change by comparing how many other catalog wallets share the old value versus the new one. Most `new:` traits come out "neutral", because the catalog doesn't cover them. Treat the hints as a starting point.

A few traits have a recommended value that wins over the head count: anti-fee-sniping nLockTime, shuffled ordering, random change position, low-R, and 0xFFFFFFFD. These are listed in `RECOMMENDED` in `score.py`.

Then write one entry per scanned PR in `data/verdicts.json`, keyed by `owner/repo#number`:

- **green.** The transactions move toward what most wallets do, or a rare pattern goes away. Examples: one common nSequence instead of a mix; payjoin receivers avoiding UIH2; swap claims becoming plain key-path spends.
- **red.** The transactions get easier to single out. Examples: a value no catalog wallet uses (nVersion 3 alone, a unique input order, change sent back to the spent script); skipping UIH2; a distinctive fee source.
- **skip.** No clear on-chain effect in practice, a mixed effect with no net direction, or testnet-only or dormant drafts. Skips stay in the file with a reason so the next rescan doesn't judge them again.

Reason style: one sentence, about 16 words or fewer, saying what an observer would notice. Spell out jargon once, e.g. "the unnecessary-input check (UIH2)". Start with "Optional" for opt-in features.

Each red or green verdict also lists the catalog wallets the PR moves toward and away from. These feed the collapsible lists and the wallet filter on the page.

```json
"owner/repo#123": {
  "verdict": "red",
  "reason": "...",
  "toward": {"Payjoin unnecessary-input check (UIH2)": ["Cake Wallet"]},
  "away": {"Payjoin unnecessary-input check (UIH2)": ["ldk-node", "Liana", "Boltz"]}
}
```

- **toward:** wallets whose catalog value already matches the new behavior.
- **away:** wallets whose catalog value matches the old behavior.
- Use the exact catalog wallet names, and leave out the PR's own wallet. For BDK PRs, the own wallet is ldk-node.
- Group the wallets by a short, plain trait label, and reuse labels already in the file, e.g. "nSequence", "Input order", "Taproot key-path spends".
- Ignore "N/A" catalog values.
- Leave both empty (`{}`) when the catalog doesn't cover the trait. The PR still shows on the page, but without a wallet list.
- Fill these in by hand from `data/trait_distribution.json`. Matching the scan text against the catalog automatically gives misleading results: before and after often contain the same catalog phrase and cancel out.

Keep verdicts for PRs that are still open. `build.py` lists verdicts whose PR left the scans, because it was closed or merged; delete those.

## Build

```
python3 build.py
```

This writes `index.html` with the data inlined, so the page works offline and from `file://`. The "as of" date comes from the newest scan file. The output lists PRs that still need a verdict.

## Catalog discrepancies found in the November 2026 scan

These are worth reporting to Armin. Check whether they're fixed before relying on these catalog rows:
- **BTCPay automatic payouts** build transactions with NBitcoin's TransactionBuilder directly and skip NBXplorer's sampling. They look like nVersion 1, nLockTime 0, nSequence 0xFFFFFFFF, shuffled, always low-R. The catalog row describes the wallet-send path only.
- **Boltz nSequence:** boltz-core master uses 0xFFFFFFFD (`ENABLE_RBF_NO_LOCKTIME`), while the catalog says 0xFFFFFFFF.
- **Boltz UIH2:** "yes" comes from an older revision of boltz-backend#1430. The current head picks the smallest fitting UTXO with no UIH check.
- **Bull Bitcoin nSequence:** Bull's code comments say bdk_dart defaults to 0xFFFFFFFD. The catalog says 0xFFFFFFFF.

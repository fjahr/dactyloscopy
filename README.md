<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="logo/dactyloscopy-logo-dark.svg">
    <img alt="Dactyloscopy" src="logo/dactyloscopy-logo.svg" width="420">
  </picture>
</h1>

Wallets give themselves away through small choices in how they build transactions. Dactyloscopy lists open pull requests in Bitcoin wallets that would change those choices:

- **Green:** the transactions move toward what most wallets already do.
- **Red:** the transactions get easier to single out.

Wallets and their current fingerprints come from Armin Sabouri's [walletfingerprints.info](https://github.com/arminsabouri/walletfingerprints.info).

## View

`index.html` is self-contained. Open it in a browser, or serve the folder with `python3 -m http.server`.

`prs.json` has the same list in machine-readable form, for review bots. The maintainer note on the page has instructions to paste into a bot's configuration.

## Update

`RESCAN.md` describes how to scan for new pull requests, judge them and rebuild the page with `python3 build.py`.

# Dactyloscopy

Wallets give themselves away through small choices in how they build transactions. Dactyloscopy lists open pull requests in Bitcoin wallets that would change those choices:

- **Green:** the transactions move toward what most wallets already do.
- **Red:** the transactions get easier to single out.

Wallets and their current fingerprints come from Armin Sabouri's [walletfingerprints.info](https://github.com/arminsabouri/walletfingerprints.info).

## View

`index.html` is self-contained. Open it in a browser, or serve the folder with `python3 -m http.server`.

## Update

`RESCAN.md` describes how to scan for new pull requests, judge them and rebuild the page with `python3 build.py`.

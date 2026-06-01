# Trevinium Activation Backend

This folder contains a minimal FastAPI activation service for direct APK sales:

- verifies Gumroad license keys on first activation
- stores install seats in SQLite
- issues signed activation tokens for offline app use
- supports periodic revalidation
- supports manual revocation/deactivation

This backend is intentionally isolated from the website files so it can live in the same GitHub repo without changing the landing pages.

Important:

- GitHub Pages cannot run this backend.
- To serve this from `trevinium.com`, run it on a server and reverse-proxy a subpath such as `https://trevinium.com/activation`.

Use [ACTIVATION_BACKEND_SETUP.md](/Users/trevino/Desktop/treviniumwebsite%20exsperimenental/ACTIVATION_BACKEND_SETUP.md) for the deployment layout in this repo copy.

# 006 — GitHub Pages Deployment & Base-Path Safe PWA

Status: Approved · Owner: Orchestrator (Gemini 4 Neon XHigh)

## Overview
Deploy **«رحلة العمرة»** automatically to GitHub Pages at `https://mohamedjs.github.io/umrah-journey/` via GitHub Actions on every push to `main`, while keeping the existing Railway deploy (`https://rehlat-al-umrah.up.railway.app`, built via Railpack `npm run build`) working unchanged.

## File Layout & Responsibilities

| Path | Responsibility |
|---|---|
| `vite.config.js` | Sets `base: process.env.VITE_BASE || './'`. Default `npm run build` keeps `./` (works on Railway `/` and local Apache subpaths); GitHub Pages workflow builds with `VITE_BASE=/umrah-journey/`. |
| `.github/workflows/pages.yml` | GitHub Actions workflow triggered on `push` to `main`, `pull_request` (build verification job), and `workflow_dispatch`. Builds with `VITE_BASE=/umrah-journey/ npm run build`, verifies `dist/` integrity, uploads Pages artifact, and deploys via `actions/deploy-pages@v4` on `main`. |
| `src/game/hud/hud.css` | Fix `@font-face` URLs from root-absolute `/fonts/...` to relative `../../../public/fonts/...` OR Vite-safe `/fonts/...` — specifically: check how Vite 8 handles `url('/fonts/...')` vs `url('./fonts/...')` vs loading fonts in `index.html` `<style>` so fonts resolve identically under **both** `base: './'` and `base: '/umrah-journey/'`! (Best solution: move `@font-face` declarations with relative `url('fonts/...')` into an inline `<style>` in `index.html`, OR keep `/fonts/...` when Vite rewrites it — moving the 4 tiny `@font-face` lines into `index.html` guarantees `url('fonts/tajawal-...')` resolves against `index.html`'s directory under BOTH `./` and `/umrah-journey/`!) |
| `src/game/loaders.js` & `src/game/voice.js` | Resolve all runtime asset URLs (`draco/`, `models/`, `audio/manifest.json`, `audio/...`) relative to `import.meta.env.BASE_URL` (e.g., `new URL(relPath, document.baseURI).href` or `${import.meta.env.BASE_URL}${relPath}`) so every fetch works whether served at `/`, `/umrah-journey/`, or `/umrah-journey` (without trailing slash). |
| `public/manifest.webmanifest` | Keeps relative `"id": "./"`, `"start_url": "./"`, `"scope": "./"`, and relative `"icons/..."` paths, which automatically resolve to `/umrah-journey/` when served from `/umrah-journey/manifest.webmanifest` and `/` on Railway! |
| `tools/vite-pwa.js` & `src/pwa/sw.js` | Emits `dist/sw.js` with relative precache URLs resolved against `self.registration.scope` (`new URL(u, scope)`). Marks large chapter environment GLBs (`^models/env/(?!kaaba|haram_mataf|maqam)`) and voice audio (`^audio/(?!manifest\.json)`) as `OPTIONAL` so core shell + Draco + heroes + title backdrop precache fast and reliably on mobile, while other chapters cache seamlessly in background / on first play. |
| `index.html` | Uses relative `manifest.webmanifest`, `icons/...`, `fonts/...` links (and Vite rewrites or preserves them cleanly under `base`). |

## GitHub Pages Workflow Design (`.github/workflows/pages.yml`)
- **Job 1 (`build`)** — runs on both `pull_request` and `push` to `main`:
  - `actions/checkout@v4`
  - `actions/setup-node@v4` (`node-version: 22`, `cache: npm`)
  - `npm ci`
  - `VITE_BASE=/umrah-journey/ npm run build`
  - Sanity checks: `dist/index.html`, `dist/sw.js`, `dist/manifest.webmanifest`, `dist/draco/draco_decoder.wasm`, and all expected `dist/models/characters/*.glb` & `dist/models/env/*.glb` exist and are non-empty.
  - Uploads Pages artifact on `push` to `main` (or `workflow_dispatch`).
- **Job 2 (`deploy`)** — runs only when `github.ref == 'refs/heads/main'` (`needs: build`):
  - `actions/configure-pages@v5`
  - `actions/deploy-pages@v4`
  - Outputs `page_url` (`https://mohamedjs.github.io/umrah-journey/`).

## Acceptance Checks
1. Local build with default base (`npm run build`) succeeds and serves cleanly at `http://127.0.0.1:4173/` (Railway simulation) with zero 404s.
2. Local build with GitHub Pages base (`VITE_BASE=/umrah-journey/ npm run build`) succeeds and serves cleanly at `http://127.0.0.1:4173/umrah-journey/` with zero 404s for JS, CSS, Tajawal fonts, Remix Icons, manifest, service worker, Draco decoder, GLB models, and audio files.
3. Service worker registers cleanly at `/umrah-journey/sw.js` with scope `.../umrah-journey/`, precaches core assets without throwing, and intercepts requests cleanly.
4. PR from `redesign/realistic` → `main` passes the GitHub Actions `build` check.
5. After merging to `main`, GitHub Pages deploys live at `https://mohamedjs.github.io/umrah-journey/` and loads with HTTP 200 and zero console errors in Chrome.

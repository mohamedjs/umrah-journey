# 001 — Full realistic redesign (handoff brief for Gemini 4 Neon)

Status: Ready · Owner: Mohamed · Written by Claude Opus 5.5 on 2026-11-25

## Your role
- **You (Gemini 4 Neon XHigh) are the orchestrator.** You plan, write the design
  docs, split the work, review every result and own the final quality.
- **Implementation goes to Gemini 4 Neon High.** Hand each well-scoped piece to
  Neon High sub-agents (your own sub-agent tool if it lets you choose the model,
  otherwise `agy -p --model gemini-4-neon-high --mode accept-edits "<brief>"` run
  from the repo root). Each brief must stand alone. Review the diff and run the
  checks yourself after each piece.
- Work on your own until it's done. Ask Mohamed only for real decisions.

## The project
`/var/www/html/old/umrah-journey` — «رحلة العمرة», a 3D story game for the web and phones
that walks the player through an Umrah, from leaving home to the end of the rites.
Read `CLAUDE.md` and `README.md` first. They hold the story, the chapters, the religious
content rules and the stack. **The rules in CLAUDE.md are binding.**

Current state: Vite + React Three Fiber prototype with chapters 1–7 (home, airport,
plane/miqat, Makkah, Tawaf, the two rak'ahs and Zamzam, Sa'i). The visuals are
procedural "clay" geometry. All lines are in `src/game/content.js`, and the voices
are in `public/audio/`. The working tree has uncommitted PWA work
(`src/pwa/`, `public/manifest.webmanifest`, `public/icons/`, `tools/vite-pwa.js`, …).
Keep that work. Create a branch `redesign/realistic`, commit the current work there
first as "WIP: PWA setup", then build on top of it.

## The goal: redesign everything, more realistic
1. **Characters:** fully redesign the player and الحاج حسن, plus the flight attendant,
   the hotel/Haram guide and the crowds. Make them realistic humans with good proportions,
   real clothing (ihram towels draped properly, abayas and hijabs), and walk/idle/pray animations.
   - Faces must still have **no features** (no eyes, nose or mouth): a smooth face only.
   - Never depict the Prophet ﷺ or any Companion.
2. **Places:** redesign all of them in a realistic style:
   - the home and the airport (counter and gate);
   - the plane cabin and lavatory;
   - the Makkah hotel and the street to the Haram;
   - the Haram: white marble, colonnades, minarets;
   - the Kaaba: black kiswa with the gold band, gold door, silver frame at the Black
     Stone, Hijr Ismail, Maqam Ibrahim;
   - the Mas'a between Safa and Marwa, with the green lights.
3. **All of it is built in Blender, driven by Python scripts.** Copy the approach of the
   sister project `/var/www/html/old/3d-quranic/blender/`: read `_bridge/` (`bridge.py`,
   `bx.py`, `cam.py`, `shot.py`) and the `v2`/`v3` folders, and read that project's
   `CLAUDE.md`/`README.md`. Create a `blender/` folder here with the same structure:
   - one script per asset or scene, re-runnable from the command line
     (`blender -b -P blender/<script>.py`);
   - export **glTF/GLB** to `public/models/`, compressed (Draco or meshopt) with baked
     textures and LODs;
   - characters rigged, with the animation clips in the GLB.
4. **Load the GLBs into the game** (HTML/R3F, `useGLTF` + animation mixer) in place of
   the procedural geometry. Keep all the game logic, rites, HUD, dialogue, voices and
   the autopilot/`?cine` mode working.
5. **Performance on phones is a hard requirement.** Keep the Lite quality mode as the
   default:
   - instanced or low-poly crowds;
   - a texture budget;
   - test at phone width in portrait and in landscape.
6. **Deploy to GitHub Pages.** Repo: `git@github.com:mohamedjs/umrah-journey.git`.
   - Add a GitHub Actions workflow that builds with Vite and deploys to Pages. Set
     `base` correctly for `/umrah-journey/`, and make sure the PWA service worker and
     manifest paths work under that base.
   - Push the branch, open a PR to `main`, and once the checks pass merge it so Pages
     goes live. Report the Pages URL at the end.
   - The existing Railway deploy stays as it is.

## Rules
- Icons: Remix Icon only (`ri-*-line`). No emoji as icons. HUD: Arabic RTL, Tajawal font.
- Don't change the religious content (rites, du'as, rulings in `content.js` and
  `docs/SOURCES.md`) without flagging it.
- Never print or commit secrets (`~/.config/lura/keys.json`).
- No background music anywhere.
- Write your design docs in `docs/` as `002-…md`, `003-…md`, etc. (one per area:
  characters, environments, Blender pipeline, R3F integration, Pages deploy).
  Each doc lists every file path, what each file is responsible for, and the
  acceptance checks.

## Done means
- `npm run build` passes and every chapter plays from start to finish with the new
  Blender assets. Check this in a real browser, desktop and phone width.
- The Blender scripts regenerate every GLB from scratch.
- It's live on GitHub Pages. Send the URL plus a short summary: what changed, what was
  checked, and what is left.

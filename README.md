# رحلة العمرة — Umrah Journey (prototype)

This is a playable prototype of the journey from **Chapter 1 to Chapter 7**. It is code only, with no Blender assets yet, and uses the same stack as «رحلة مع القرآن». The chapters play one after another (the title screen's «ابدأ الرحلة» button), and each one can also be opened on its own.

| # | Chapter | What you do |
|---|---|---|
| 1 | البيت | Pack the bag (passport and visa, ihram clothes, sandals); the perfume choice (on the body before ihram, not packed to use in ihram); the du'a for leaving home |
| 2 | المطار | Check in at the counter, go to gate 12, the travel du'a |
| 3 | الطيارة والميقات | The captain's miqat announcement and a countdown; wudu and putting on ihram in the lavatory; at the miqat the niyyah «لبيك اللهم عمرة» and the talbiyah; the ihram prohibitions |
| 4 | مكة | The hotel guide gives the key; talbiyah on the way (the «لبّيك» button / T); entering al-Masjid al-Haram with the right foot and the du'a; the camera glides down for the first sight of the Kaaba |
| 5–6 | الطواف, then the two rak'ahs and Zamzam | (as below) |
| 7 | السعي | (as below) |

Icons are **Remix Icon** (the `remixicon` npm package, `<i class="ri-…-line">`); no emoji are used as icons.

## Run

```bash
npm install
npm run dev            # http://localhost:5173
npm run build          # → dist/ (base './', works from any sub-path, e.g. /old/umrah-journey/dist/)
```

URL options:

| Option | What it does |
|---|---|
| `?cine` | Cinematic auto-play. The player walks by himself, dialogue moves on by itself, and the action buttons press themselves. This is the mode to record the promo video from. |
| `?q=lite\|normal` | Picks the quality. Lite is the default. The title screen has the same toggle, and the choice is saved. |
| `?speed=N` | Fast-forward with N sub-steps per frame. For testing only. |
| `window.__game` | `{ useStore, world }`, for the console. |

## Controls

| Input | Action |
|---|---|
| WASD / arrow keys | Walk. Hold Shift for raml (tawaf) or jogging between the green lights (Sa'i). |
| Touch | A fixed joystick at the bottom left. Push it to the edge to jog, or use the 🏃 button. |
| Drag | Turn the camera. |
| Mouse wheel / pinch / + − | Zoom. |
| F or 👣 | Autopilot. It walks along the right path, for example the circle in tawaf or the lane in Sa'i. |
| Enter / Space | Next line of dialogue. |
| G / E / R | The action button on screen. For example: ✋ point and say takbir (G), 🕌 pray (E), 👤 idtiba' / cover the shoulder (R). |
| ❓ | «اسأل الحاج حسن»: questions and answers for each chapter. |

## How the rites are checked (`src/game/rites/`)

### Tawaf (`tawaf.js`)

- **Progress:** the code tracks the angle walked round the Kaaba, without wrapping, from the start line at the Black Stone corner (θ = 0). Counter-clockwise adds to it and clockwise takes away, so walking backwards never counts. A circuit is done at each 2π, and tawaf is done at 7.
- **Wrong direction:** walking against the crowd, or into Hijr Ismail, only brings a gentle word from الحاج حسن. There is never a "game over".
- **Hijr Ismail:** blocked by collision, so the tawaf always goes round it.
- **Prompts along the circuit:**
  - Near the start line: «شاور وكبّر».
  - At ar-Rukn al-Yamani: a tip about touching it.
  - Between the Yamani corner and the Black Stone: a panel with «ربنا آتنا…».
- **Raml:** checked as the share of running time in circuits 1–3.
- **After the 7th circuit:**
  1. Cover the right shoulder.
  2. Walk to the glowing circle behind the Maqam.
  3. Two rak'ahs (a panel with the verse and the surahs).
  4. Zamzam.
  5. On to the Mas'a.

### Sa'i (`sai.js`)

- **Start:** it begins on as-Safa, with the verse, «أبدأ بما بدأ الله به» and the dhikr.
- **Laps:** reaching the other hill counts one lap, so lap 7 ends on al-Marwa.
- **Wrong direction:** turning back halfway does not count, and الحاج حسن comments on it.
- **Green-lit stretch:** jogging is tracked, and a panel shows the du'a narrated from the Companions.

Every line and the source for each rite are in `src/game/content.js` and `docs/SOURCES.md`. **Nothing has been reviewed by the sheikh yet.**

## Layout

```
src/game/
  chapters.js     the chapter list (order, numbers, icon, scene builder, rites)
  scenes/         home.js, airport.js, plane.js, makkah.js + kit.js (boxes, signs, wandering crowds)
  content.js      all dialogue / du'a / Q&A (ids + source keys)
  store.js        UI state (zustand), dialogue queue, tips, overlays
  refs.js         per-frame shared state (player, mentor, camera)
  Controller.jsx  movement, autopilot, mentor follow, camera, rites tick
  mataf.js        Mataf scene + crowd + collisions (Kaaba, Hijr, Maqam)
  masa.js         Mas'a scene + crowd + collisions
  people.js       faceless clay rigs (idtiba' toggle, raml gait) + instanced crowd
  rites/          home.js, airport.js, plane.js, makkah.js, tawaf.js, sai.js, stats.js, kit.js (hotspots, talbiyah)
  hud/            Hud.jsx (objective, counter, minimap, tags, dialogue, Q&A), hud.css
tools/
  export_voice_lines.mjs   content.js → tools/voice_lines.json
  openrouter_tts_lines.py  Gemini TTS through OpenRouter (copied from the Quran game)
  voice_import.py          wavs → public/audio + manifest.json (the game plays them if present)
```

## Voices

The owner runs these on his own terminal, because openrouter.ai is not reachable from the sandbox.

```bash
npm run voice-lines
python3 tools/openrouter_tts_lines.py --limit 3      # listen first
python3 tools/openrouter_tts_lines.py
python3 tools/voice_import.py tools/voice_raw_openrouter --no-post
```

## Not done yet

- PWA / offline.
- Telemetry.
- Railway deploy.
- Blender hero assets.
- Chapter 8 (halq / taqsir) and the optional Madinah chapter.
- Going back to touch the Black Stone before Sa'i.

## Deploy (Railway)

- **Railway:** project `umrah-journey` → service `umrah-web`. It is a small Bun function that serves the build from the `game-files` bucket.
- **Link:** https://umrah-web-production.up.railway.app
- **Update it:** run `bash tools/upload_to_railway.sh` from your own terminal. It builds the game, uploads the build, then clears the service's cache.
- **Upload secret:** it lives in `tools/.railway-upload-token` (gitignored). It is the same value as the service's `UPLOAD_TOKEN` variable.
- **Later, with GitHub:** connect the repo to a normal Railway service (build `npm run build`, serve `dist/`) and delete the function + bucket.

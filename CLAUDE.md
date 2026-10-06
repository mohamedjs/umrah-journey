# رحلة العمرة — Umrah Journey (3D story game)

A 3D story game for the web and phones that takes the player through an Umrah, from leaving home until the rites are finished. The same scenes also have a cinematic auto-play mode, and the promo / explainer motion-graphics video is recorded from that mode.

Sister project: `/var/www/html/old/3d-quranic` («رحلة مع القرآن»). Copy its approach (React Three Fiber, Lite quality by default, the PWA/offline setup, voice pipeline, telemetry, Railway hosting) instead of reinventing it. Read its CLAUDE.md / README first.

## Status
- Concept only. `concept/` holds four still mock-ups rendered with plain three.js. They show the art direction and HUD:
  - `umrah_1_home.jpg`, `umrah_2_plane.jpg`, `umrah_3_tawaf.jpg`, `umrah_4_sai.jpg`
  - Source: `concept/index.html` + `concept/scene.js`, with `?s=1..4` selecting the scene.
  - To view them: `cd concept && npm i three@0.170 && python3 -m http.server`, then open `index.html?s=3`. The import map expects `./three/` → `node_modules/three` (symlink or copy it).
- Next step agreed with the owner: build a **playable prototype of Chapter 4 (Tawaf) + Chapter 5 (Sa'i)** in code only, with no Blender yet. Once the look and feel are approved, bring in Blender for hero assets.
- **Prototype built (2026-10-06)**: Vite + R3F app at the repo root (`npm run dev`). It plays chapter 5 (Tawaf: idtiba', the start line and the gesture at the Black Stone, 7 counted circuits, raml, the Yamani tip and «ربنا آتنا…», Hijr blocked), a short chapter 6 (two rak'ahs behind the Maqam, Zamzam) and chapter 7 (Sa'i: Safa dhikr, 7 laps, the green-lit stretch), plus «اسأل الحاج حسن» Q&A, the minimap, autopilot (F), touch joystick, `?cine` auto-play and `?q=lite|normal`. The HUD uses the list numbering below (5 = Tawaf, 7 = Sa'i).
  - Read `README.md` for the layout and how the rites are checked.
  - All lines live in `src/game/content.js`, each with a `src` key. `docs/SOURCES.md` holds the references and flags the madhhab differences (⚠️) and the reference numbers still to check (🔎) for the sheikh.
  - Voices: `npm run voice-lines` → `tools/openrouter_tts_lines.py` (Egyptian-dialect instructions) → `tools/voice_import.py`. The game plays `public/audio/manifest.json` if present.
  - **Chapters 1–4 added (2026-10-06)**: home (packing + perfume choice), airport (counter → gate 12), plane (miqat countdown, wudu + ihram in the lavatory, niyyah + talbiyah), Makkah (hotel guide → gate with the entry du'a → camera glides down onto the Kaaba). «ابدأ الرحلة» plays them in order; `src/game/chapters.js` lists them.
  - Icons: **Remix Icon** only (`remixicon` package, `ri-*-line` classes). No emoji as icons.
  - **Railway (2026-10-06)**: https://umrah-web-production.up.railway.app — a Bun function serving the `game-files` bucket. Update it with `bash tools/upload_to_railway.sh` (owner's terminal; the token is in `tools/.railway-upload-token`). The plan is to switch to a GitHub-connected service later.
  - Not done yet: PWA, telemetry, chapter 8 and Madinah, going back to touch the Black Stone before Sa'i.

## Story & chapters
The player is a man whose body is shown but whose face has no features (no eyes, nose or mouth). The mentor **الحاج حسن** is an older man who has done Umrah before. He walks with the player, answers questions, and corrects mistakes gently (never "game over"). Other people the player meets: the flight attendant, the captain's announcement, and a hotel / Haram guide.

1. **البيت:** pack the Umrah bag with a checklist mini-game.
   - Items: passport and visa, ihram clothes, comfortable sandals.
   - Perfume is a trap item: it may be used before ihram only.
2. **المطار:** check-in, then the gate.
3. **الطيارة والميقات:**
   - The captain announces the miqat about 20 minutes ahead.
   - Before the miqat: wear ihram and make wudu.
   - At the miqat: make the niyyah «لبيك اللهم عمرة» and start the talbiyah.
4. **مكة:** arrive at the hotel and see the Haram for the first time.
5. **الطواف:**
   - 7 circuits, starting at the Black Stone corner, with the Kaaba on the left.
   - At the Black Stone: gesture with the right hand and say «بسم الله والله أكبر».
   - For men: idtiba' (right shoulder uncovered) and raml in the first three circuits.
   - HUD shows a circuit counter and a minimap.
6. **بعد الطواف:** two rak'ahs behind Maqam Ibrahim, then Zamzam.
7. **السعي:**
   - 7 laps from Safa to Marwa.
   - Men walk faster between the green lights.
8. **الحلق أو التقصير:** end of Umrah.
9. **Optional — المدينة:** al-Masjid an-Nabawi, ar-Rawdah, Quba.

Later the owner may add Hajj as a separate story.

## Religious content rules
- Never depict the Prophet ﷺ or any Companion.
- People have faces without features.
- Every rite, du'a and ruling must come from a reliable source. Flag topics where the madhhabs differ instead of picking one silently.
- The owner will have a sheikh review the content before release.
- Dar al-Ifta fatwa on teaching the rites with a Kaaba model (read before release): https://www.dar-alifta.org/ar/fatwa/details/11977
- No invented details in the story. Keep it simple and respectful.

## Art direction (from the concept)
- Soft stylized "clay" look with warm light. The HUD is Arabic RTL in the Tajawal font:
  - an objective card at top right and a chapter pill at top left;
  - a checklist / counter under the objective;
  - a dialog box at the bottom with the speaker name tag.
- Kaaba: black kiswa with a gold band, gold door, a silver frame at the Black Stone corner, the low semicircle of Hijr Ismail, and the Maqam Ibrahim dome.
- Haram: white marble with a ring colonnade and minarets.
- Crowds: instanced simple figures, mostly in white ihram, with women in abayas and hijabs. Keep it light on weak devices.
- The owner may still choose a more realistic look, or a more anime look like the Quran game. Ask before committing to the final style.

## Tech decisions
- Same stack as the Quran game: Vite + React Three Fiber (three.js), Lite quality by default, and a PWA.
- Blender is optional at first. Use it later, driven by scripts (as in the Quran game's `blender/` bridge), for the detailed Haram / Kaaba and for animated characters.
- Voices: Gemini TTS through OpenRouter (model `google/gemini-3.8-flash-lite-tts`). Each character gets its own voice and tone.
  - Script template: `3d-quranic/tools/openrouter_tts_lines.py`.
  - Key: `~/.config/lura/keys.json` → `"openrouter"`. Never print it or commit it.
  - openrouter.ai is only reachable from the owner's own terminal, so he runs the TTS scripts himself.
- Dialogue language: Egyptian colloquial Arabic for the mentor's conversation. Quran, du'a and talbiyah text stays in fusha with tashkeel.
- Language with the owner: when he writes in Arabic, reply in Egyptian colloquial Arabic.

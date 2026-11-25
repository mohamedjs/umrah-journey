# 005 — React Three Fiber GLB Integration, Animation Mixer & Phone Performance

Status: Approved · Owner: Orchestrator (Gemini 4 Neon XHigh)

## Overview
Replaces all procedural "clay" geometry in `src/game/` with the Draco+WebP Blender GLBs while preserving **100% of game logic, rites (`src/game/rites/`), religious text (`src/game/content.js`), HUD, voices, touch joystick, autopilot (`F`), `?cine` auto-play, `?speed=N`, and `?q=lite|normal`**.

## File Layout & Responsibilities

| Path | Responsibility |
|---|---|
| `public/draco/*` | Local Draco WASM/JS decoder (`draco_decoder.js`, `draco_decoder.wasm`, `draco_wasm_wrapper.js`) so GLBs decode offline in PWA & GitHub Pages with zero external CDN calls. |
| `src/game/loaders.js` | Shared singleton `GLTFLoader` configured with local `DRACOLoader` (`new URL('./draco/', document.baseURI)` / relative `./draco/`) and `MeshoptDecoder`; promise-cached `loadGLTF(url)`, R3F `useGLTF(url)` + `useGLTF.preload(url)` hook, `applyLOD(root, qualityName)` helper (toggles `*_LOD0` vs `*_LOD1` + configures shadow flags), and `setupMaterials(root, shadows)` for crisp PBR response. |
| `src/game/characterRig.js` | Loads rigged character GLBs (`player`, `mentor`, `attendant`, `guide`, `agent`), clones cleanly via `SkeletonUtils.clone()`, creates `THREE.AnimationMixer`, exposes the exact hero contract `{ group, head, setOutfit('street'\|'ihram'), setIdtiba(bool), animate(dt, speed, { running, raise, pray, talk }), idtiba, outfit }`, smoothly crossfades `idle` / `walk` / `run` / `talk` / `gesture` / `pray` clips, and matches walk/run `timeScale` to ground speed to prevent foot sliding. |
| `src/game/people.js` | Exports `makeGlbPerson(key, opts)` (synchronous wrapper group populated immediately when cached GLB resolves — or awaited via preloaded scene assets) AND realistic GLB-backed `makeCrowd(n, rnd, opts)` using `crowd.glb` archetypes (`InstancedMesh` per archetype part: ihram idtiba', ihram covered, street men, women in abayas/hijabs, seated passengers) with per-instance `setColorAt` for skin & clothing variation and subtle walking bob/stride lean. Keeps lightweight fallback only if a GLB fails to load. |
| `src/game/Game.jsx` | Preloads core character GLBs + active chapter GLBs cleanly before mounting the scene (updating `#loading` progress text so the player never sees bare clay placeholders), attaches a procedural `PMREMGenerator` + `RoomEnvironment` IBL (`scene.environment`, intensity ~0.55–0.75) for realistic gold/silver/marble/glass reflections at 0 KB download cost, configures `THREE.ACESFilmicToneMapping` (`toneMappingExposure: 1.05`), and keeps `TitleBackdrop` rendering the new realistic Mataf & Kaaba GLBs. |
| `src/game/quality.js` | Keeps `lite` as default. Sets balanced realistic instanced crowd counts (`lite`: `tawafCrowd: 56, saiCrowd: 36, airportCrowd: 40, makkahCrowd: 70`; `normal`: `tawafCrowd: 140, saiCrowd: 84, airportCrowd: 95, makkahCrowd: 160`) and `lod: 'LOD1' | 'LOD0'`. |
| `src/game/mataf.js` | Loads `kaaba.glb`, `maqam.glb`, and `haram_mataf.glb` into `buildMataf()`, keeps the glowing gameplay start line at `θ = 0`, preserves all exports (`H`, `R`, `KAABA_H`, `HIJR`, `MAQAM`, `MATAF_R`, `ang`, `polar`, `maqamPos`, `prayPos`, `blackStone`, `yamaniPos`, `collideMataf`, `matafLayout`), and drives the realistic instanced counter-clockwise crowd. |
| `src/game/masa.js` | Loads `masa.glb` into `buildMasa()`, preserves all exports (`LEN`, `HALF_W`, `GREEN`, `SAFA_Z`, `MARWA_Z`, `KAABA_HEADING`, `collideMasa`, `masaLayout`), and drives the realistic two-lane instanced crowd (men jogging faster in the green zone). |
| `src/game/scenes/home.js` | Loads `home.glb`, binds `take(key)` to hide `item_passport` / `item_ihram` / `item_sandals` / `item_perfume` nodes + floating golden rings, binds `showDoor(on)` to the exit floor ring, preserves `HOME_SPOTS` and `homeLayout`. |
| `src/game/scenes/airport.js` | Loads `airport.glb` + rigged `agent.glb` (animated idle/talk behind counter), mounts crisp Arabic canvas signs from `kit.js` onto the signboard housings, drives realistic wandering travellers, preserves `AIRPORT_SPOTS` and `airportLayout`. |
| `src/game/scenes/plane.js` | Loads `plane.glb` + rigged `attendant.glb` (animated idle/talk near rear galley), places realistic **seated** man & woman passenger `InstancedMesh` crowds into cabin seats, keeps glowing lavatory floor ring, preserves `PLANE_SPOTS` and `planeLayout`. |
| `src/game/scenes/makkah.js` | Loads `makkah.glb` + rigged `guide.glb` (animated idle/talk at hotel desk), mounts crisp Arabic hotel sign, drives realistic pilgrims walking toward the Haram gate, preserves `MAKKAH_SPOTS` and `makkahLayout`. |
| `src/game/Controller.jsx` | Minor hook preservation: passes `{ talk, running, raise, pray }` to `heroes.player.animate(...)` and `heroes.mentor.animate(...)`; also ticks ambient NPCs (`scene.update` animates `agent`, `attendant`, `guide` mixers smoothly). |

## Asset Loading Strategy (Zero Layout Shift / Zero Missing Meshes)
- All shared character GLBs (`player.glb`, `mentor.glb`, `crowd.glb`) + the active chapter's GLB(s) are loaded via `preloadChapterAssets(chapterId)` inside `Scene` (or React `<Suspense>` using `useGLTF`).
- Using `<Suspense fallback={null}>` with a clean `useGLTF(url)` hook (following standard R3F idioms!) guarantees that when a chapter renders:
  1. Every GLB mesh is already decoded and mounted on frame 1.
  2. `scene.take(k)` in `home.js` and `setOutfit`/`setIdtiba` in `tawaf.js`/`plane.js` operate synchronously on real GLB meshes immediately — zero race conditions in `?cine` or `?speed=N`!
  3. Switching chapters shows a brief subtle loading overlay only if that chapter's GLB isn't cached yet, and we eagerly preload the next chapter in the background (`useGLTF.preload(...)`) once the current chapter starts!

## Lighting & Realistic Material Tuning
- `Canvas` renderer: `toneMapping: THREE.ACESFilmicToneMapping`, `toneMappingExposure: 1.05`, `outputColorSpace: THREE.SRGBColorSpace`.
- Procedural `RoomEnvironment` IBL generated once via `PMREMGenerator` and assigned to `scene.environment` with `scene.environmentIntensity = 0.55` (softened in night/twilight chapters like `mataf` and `makkah` to `0.45`, brighter `0.65` in daytime `home`/`airport`/`masa`).
- Material shadow setup: `castShadow = Q.shadows` and `receiveShadow = Q.shadows` on all environment & character meshes (except emissive lights/windows/glow rings).

## Phone Performance Guardrails (Lite Default)
- **Draw calls per scene in Lite mode**: target **≤ 60 draw calls** (instanced crowds ≤ 12 draw calls total, environment ≤ 25 draw calls, hero + mentor ≤ 12 draw calls).
- **Triangles per frame in Lite mode**: target **≤ 90k triangles** (using `*_LOD1` meshes + low-poly instanced crowds).
- **Memory**: Proper disposal of per-chapter geometries/materials/mixers only on cloned resources; shared cached GLTF scenes stay resident across chapter hops.
- **Responsive Viewport**: Portrait phone (`390×844`) uses wider FOV (`68°`), landscape phone (`844×390`) uses `50°`, HUD & touch joystick never collide with dialogue or action buttons.

## Acceptance Checks
1. `npm run build` completes with zero errors and emits cleanly chunked JS (`three`, `react`, app) + `sw.js`.
2. Zero console errors, zero 404s, zero WebGL warnings across Title + all 6 chapters (`home`, `airport`, `plane`, `makkah`, `tawaf`, `sai`).
3. Every chapter plays end-to-end (verified via real Chrome browser with `?cine&speed=4` and manual checks):
   - Home: items disappear when picked up, perfume trap works, door opens.
   - Airport: check-in agent visible & animated, gate 12 works.
   - Plane: flight attendant animated, seated passengers sit properly in seats, outfit switches seamlessly from street → ihram after lavatory.
   - Makkah: hotel guide animated, pilgrims walk to Haram gate, transition glides down onto Kaaba.
   - Tawaf: idtiba' switches rida mesh to bare right shoulder; 7 circuits, Black Stone gesture raises right arm, cover shoulder switches rida back, pray behind Maqam plays prayer animation, Zamzam transitions to Sa'i.
   - Sa'i: Safa/Marwa granite hills & green lights render clearly, 7 laps finish with End summary screen.
4. Tested at desktop (`1280×720`), phone portrait (`390×844`), and phone landscape (`844×390`).

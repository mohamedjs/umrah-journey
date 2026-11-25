# 004 — Realistic Blender Environments & Architectural Landmarks

Status: Approved · Owner: Orchestrator (Gemini 4 Neon XHigh)

## Overview
All 6 playable environments (covering Chapters 1–7) are rebuilt in Blender Python with realistic architectural proportions, physically based textures, baked geometric AO, and `LOD0` / `LOD1` pairs where beneficial. Every environment matches the **exact world coordinates, hotspots, and collision footprints** of the existing game logic so all rites, minimaps, autopilot paths, and floating tags stay 100% accurate.

## File Layout & Responsibilities

| Path | Output GLB | Responsibility |
|---|---|---|
| `blender/env/__init__.py` | — | Package marker. |
| `blender/env/home.py` | `public/models/env/home.glb` | Chapter 1 warm Egyptian bedroom diorama + 4 interactive takeable item nodes. |
| `blender/env/airport.py` | `public/models/env/airport.glb` | Chapter 2 international airport departures hall + parked airliner outside glass facade. |
| `blender/env/plane.py` | `public/models/env/plane.glb` | Chapter 3 commercial airliner cabin, 14 seat rows, sunset windows, galley cart & rear lavatory. |
| `blender/env/makkah.py` | `public/models/env/makkah.glb` | Chapter 4 Makkah hotel portico & lobby, marble plaza, Haram stone arcade exterior, grand gate, twin minarets & distant clock tower silhouette. |
| `blender/env/kaaba.py` | `public/models/env/kaaba.glb` | Chapters 5–6 hero Kaaba: black woven silk Kiswa, embroidered gold Hizam & cartouches, gold Bab al-Kaaba, Shadharwan plinth, Black Stone in hammered silver frame, Mizab al-Rahmah, and marble Hijr Ismail with lanterns. |
| `blender/env/maqam.py` | `public/models/env/maqam.glb` | Chapters 5–6 Maqam Ibrahim: octagonal marble plinth, ornate golden/brass cage, glass enclosure, ribbed golden dome & finial. |
| `blender/env/haram_mataf.py` | `public/models/env/haram_mataf.glb` | Chapters 5–6 Mataf white Thassos marble courtyard, multi-tiered arched Haram colonnade, hanging lanterns, 6 sculpted multi-tiered minarets, and green Black Stone line marker lamp. |
| `blender/env/masa.py` | `public/models/env/masa.glb` | Chapter 7 Al-Mas'a gallery: marble floor, central balustrade, fluted columns & pointed arches, brass chandeliers, glowing green Milayn al-Akhdarayn ceiling/pillar lights, realistic granite Safa & Marwa hills with marble/brass railings. |
| `blender/env/build_all.py` | all above | Master environment build entry point + budget JSON report + preview renders in `blender/previews/env_*.png`. |

## Exact Coordinate & Node Contracts (Three.js World Space)
Every Blender script converts Three.js world coordinates `(tx, ty, tz)` using `three_to_bl(tx, ty, tz) = Vector((tx, -tz, ty))`.

### 1. Home (`home.glb`) — Bounds `x ∈ [-8, 8], z ∈ [-7, 7]`
- **Architecture**: Oak hardwood floor (`y=0`), back wall (`z=-7.05`), left wall (`x=-8.05`) with baseboards & crown molding; morning-sunlit recessed mullioned window (`x=1.5, y=3.8, z=-6.92`) with warm sheer curtains; ornate woven rug (`x=0.5, z=1.0`, oval `6.4×4.5 m`).
- **Furniture (matching collision boxes)**:
  - Bed: `x ∈ [-6.4, -1.4], z ∈ [-6.9, -2.2]` — sculpted oak frame, headboard, plush mattress, folded duvet, pillows, and open teal hard-shell suitcase at `(-4.2, 1.25, -4.0)` rotated `y=0.25`.
  - Bookshelf / cabinet: `x ∈ [4.4, 6.8], z ∈ [-6.9, -4.6]`, top at `y=2.2`, potted lush indoor plant on back corner `(4.9, 2.2, -6.3)`.
  - Dresser + framed wall mirror: `x ∈ [-7.95, -6.5], z ∈ [1.1, 3.5]`, top at `y=1.3`, beveled mirror on left wall above.
  - Front door frame & ajar paneled wood door with brass handle at `(7.3, 0, 6.3)` rotated `y=-π/2`.
- **Named takeable item nodes** (R3F `take(key)` sets `.visible = false` on these exact node names):
  - `item_passport`: dark burgundy embossed passport + folded white boarding/visa slip at `(5.6, 2.22, -5.4)`
  - `item_ihram`: neatly stacked folded white terry-cotton ihram towels (2 towels) at `(-2.6, 1.26, -3.2)`
  - `item_sandals`: realistic pair of brown leather slip-on sandals at `(4.6, 0.02, 5.0)`
  - `item_perfume`: faceted glass oud/perfume flacon with gilded cap at `(-7.0, 1.32, 2.3)`
- **Budget**: ≤ 18,000 tris (`LOD0`), ≤ 8,000 tris (`LOD1`), ≤ 550 KB GLB.

### 2. Airport (`airport.glb`) — Bounds `x ∈ [-28, 30], z ∈ [-11.6, 12]`
- **Architecture**: Polished light terrazzo/marble floor (`64×30 m` centered `x=1, z=0`); full-height glass curtain wall with steel mullions along `z=-12.2` overlooking a tarmac apron and a realistic parked airliner at `(22, 2.6, -18)` (tapered fuselage, swept wings, twin turbofans, cockpit glass, vertical tail stabilizer); side walls at `x=-28.1` and `x=30.1`; vaulted ribbed ceiling with recessed skylight/LED strips (`y=9.2`).
- **Obstacles (matching `BOXES`)**:
  - Check-in counter island: `x ∈ [-12, 12], z ∈ [-9.2, -7.8], h=1.1` with granite counter top, workstation monitors, scales, suitcases along front, and dark slatted rubber baggage belt at `z=-10.8`.
  - Four structural clad columns at `x ∈ {-18, -6, 6, 18}, z ∈ [3.4, 4.6], h=9`.
  - Three rows of realistic airport bench seating at `x ∈ [19.5, 28.5], z ∈ {-5, -2, 1}` (metal beam + contoured individual chairs + armrests).
  - Illuminated Gate 12 portal arch/frame at `(25, 0, -11.7)`.
  - Physical hanging signboard housings at `(0, 5, -11.9)`, `(25, 5, -11.9)`, and `(14, 6, -0.5)` (crisp Arabic canvas text overlays attach cleanly in Three.js).
- **Budget**: ≤ 24,000 tris (`LOD0`), ≤ 10,000 tris (`LOD1`), ≤ 600 KB GLB.

### 3. Plane (`plane.glb`) — Cabin `x ∈ [-3.7, 3.7], z ∈ [-15.5, 12.7]`
- **Architecture**: Curved composite interior cabin shell (`r=4.2 m`, length `30 m`, centered `(0, 2.2, -1.5)`), ribbed ceiling cove panels with warm linear cabin lights, deep woven aisle carpet (`x ∈ [-0.55, 0.55]`), sculpted oval window frames along both sides (`x = ±3.85`, `z` from `-15` to `8.5` step `1.6`) with glowing warm sunset horizon panes, sculpted overhead stowage bins along both sides (`x = ±2.75, y=4.0`), front bulkhead (`z=-15.6`) with burgundy curtain & cabin crest, rear bulkhead (`z=12.8`).
- **Seats**: 14 rows (`z = -14` to `7.2`, step `1.6`) × 6 seats (`x ∈ {-3.0, -2.2, -1.4, 1.4, 2.2, 3.0}`) with sculpted ergonomic cushions, reclining seatbacks, winged headrests + white linen antimacassars, folding armrests, and metal leg frames.
- **Rear Galley & Lavatory**:
  - Lavatory enclosure matching `LAV = [1.3, 3.6, 10.0, 12.6]`, height `3.4 m`, realistic paneled bifold door facing the aisle at `x=1.3, z=11.2` with warm illuminated indicator plaque.
  - Stainless-steel galley service trolley & counter at `(-2.6, 0, 11.0)`.
- **Budget**: ≤ 26,000 tris (`LOD0`), ≤ 11,000 tris (`LOD1`), ≤ 500 KB GLB.

### 4. Makkah (`makkah.glb`) — Bounds `x ∈ [-24, 24], z ∈ [-39.6, 18.4]`
- **Plaza**: Grand cream/white marble courtyard (`90×80 m` centered `(0, 0, -12)`) with inlaid geometric stone paving borders.
- **Hotel (`z ≥ 9.5`)**:
  - Realistic sandstone/limestone Makkah hotel tower (`x ∈ [-20, 20], z ∈ [18.5, 24.5], h=30`) with recessed arched warm-lit hotel windows & carved cornices.
  - Grand entrance portico (`x ∈ [-12, 12], z ∈ [9.5, 18.5], roof y=5.6`) supported by stone columns matching `BOXES` at `x = ±11.5, z ∈ [9.6, 10.6]`.
  - Polished marble & walnut reception desk matching `BOXES` `x ∈ [-7.4, -2.6], z ∈ [15.4, 16.4], h=1.1`.
  - Signboard frame above portico `(0, 6.6, 9.45)` for «فندق ضيوف الرحمن».
- **Haram Exterior (`z ≤ -39.5`)**:
  - Monumental cream marble & sandstone Masjid al-Haram facade (`x ∈ [-50, 50], z = -42.5, h=16`) with rhythmic pointed Islamic arched niches, upper clerestory gallery & carved crenelation parapet.
  - Grand central Haram portal (`x ∈ [-5, 5], z=-40.2, h=14`) with ornate recessed pointed arch, carved brass/bronze ceremonial doors, and warm glowing golden interior passage (`x ∈ [-2.5, 2.5], z=-39.5`).
  - Twin monumental 3-tier sculpted Hijazi minarets at `(±9, 0, -42)` rising to `y=65 m` with octagonal shafts, carved muqarnas balconies, arched lanterns, ribbed domes & golden crescents.
  - Distant iconic Makkah Clock Tower silhouette at `(42, 0, -95)` rising to `125 m` with tiered setbacks, illuminated emerald-white clock dial (`y=100`), and gilded spire.
- **Plaza Lamp Posts**: 10 ornate bronze Islamic street lamp posts matching `BOXES` at `x = ±14, z ∈ {4, -4, -12, -20, -28, -36}` (`h=6 m`, glowing warm frosted glass lanterns at top).
- **Budget**: ≤ 32,000 tris (`LOD0`), ≤ 14,000 tris (`LOD1`), ≤ 750 KB GLB.

### 5. Kaaba (`kaaba.glb`) — Centered `(0, 0, 0)`, rotated `+45°` around Y
- **Dimensions**: Exact `2H = 11.6 m` square (`H = 5.8`), height `13.0 m` above the `0.4 m` sloped cream-marble **Shadharwan** plinth (`y ∈ [0, 0.4]`).
- **Kiswa**: Rich jet-black woven silk texture (1024px WebP) with subtle chevron damask weave, gentle vertical drape panels/seams, and deeply detailed metallic gold **Hizam** (belt at `y ≈ 9.2–10.3 m`) with ornate Islamic geometric/calligraphic cartouche frames, golden corner medallions, and the embroidered **Sitara** curtain panel framing the door.
- **Bab al-Kaaba** (North-East face, local `+x` near Black Stone `+z` corner at `local (H+0.03, 2.3..5.7, H-2.6)`): sculpted gold-plated double doors with recessed relief panels, central ornamental lock/knocker rings, and gilded frame.
- **Al-Hajar al-Aswad** (East corner, world `(+8.25, 1.5, 0)`): beveled hammered silver oval frame (`metalness=0.95, roughness=0.20`) recessed cleanly around the glossy dark stone cluster.
- **Mizab al-Rahmah**: Gilded rainspout extending slightly from the North-West parapet edge over Hijr Ismail.
- **Hijr Ismail (Al-Hatim)** (off North-West face, `HIJR = {a: 5.0, b: 8.0, t: 0.9}`): smooth semicircular marble wall (`h=1.32 m`) with molded coping stone, inlaid subtle marble paneling, pale marble inner floor (`y=0.02`), and 3 delicate brass lanterns along the rim.
- **Budget**: ≤ 14,000 tris (`LOD0`), ≤ 6,500 tris (`LOD1`), ≤ 550 KB GLB.

### 6. Maqam Ibrahim (`maqam.glb`) — Origin `(0, 0, 0)` (placed at `maqamPos` in Three.js)
- Tiered octagonal white/cream marble base (`r=1.0 m, h=0.5 m`), delicate gilded hexagonal frame pillars with curved arches, crystal-tinted translucent glass enclosure cylinder (`r=0.68 m`), sculpted inner brass pedestal cradle, ribbed golden dome (`y=2.1..2.85 m`), and gilded spire/crescent (`y=3.3 m`).
- **Budget**: ≤ 4,500 tris, ≤ 180 KB GLB.

### 7. Haram Mataf (`haram_mataf.glb`) — Centered `(0, 0, 0)`, `MATAF_R = 45`
- **Mataf Floor**: Polished white Thassos marble circular courtyard (`r = 53 m`) with subtle concentric radial marble tile joints & natural faint veining (1024px WebP).
- **Colonnade (`colR = 48 m`)**:
  - 2-storey monumental Haram ring arcade: `LOD0` = 48 fluted marble columns with gilded capitals + 48 true pointed Islamic arches + upper arched gallery + stone crenelated parapet + hanging warm brass chandeliers + outer marble arcade enclosure wall (`r = 60 m`).
  - `LOD1` = simplified 32-bay arcade ring with lower polygon counts for Lite phone tier.
- **6 Sculpted Minarets**: Placed at `r = 64 m`, `θ = i/6 * 2π + 0.3`, height `44 m`, multi-tiered stone shafts, carved balconies, arched upper lantern gallery & golden crescent spires.
- **East Colonnade Green Line Lamp**: Mounted at `(47.6, 5.0, 0)` facing inward toward the Black Stone.
- **Budget**: ≤ 36,000 tris (`LOD0`), ≤ 14,000 tris (`LOD1`), ≤ 750 KB GLB.

### 8. Mas'a (`masa.glb`) — Corridor `x ∈ [-10, 10], z ∈ [-137, 17]` (`LEN=120`, `GREEN=[-38,-55]`)
- **Floor & Divider**: Polished veined cream marble gallery floor (`20×154 m`) with inlaid border bands; low molded marble central balustrade divider (`x ∈ [-0.6, 0.6], z ∈ [-117, -3], h=1.05 m`) with bronze top rail.
- **Arcade & Ceiling**: Side marble walls (`x = ±10.25, h=12 m`) with recessed arched architectural bays; fluted marble columns (`x = ±9.2`, every `9 m`) with gilded capitals & graceful pointed transverse ceiling arches; coffered ceiling (`y=12.2 m`) with suspended brass Islamic chandeliers (`x = ±5`, every `12 m`).
- **Milayn al-Akhdarayn (Green Lights, `z ∈ [-38, -55]`)**: Prominent glowing emerald LED ceiling beams at `z = -38` and `z = -55`, green illuminated pillar collars at `x = ±9.2`, longitudinal green ceiling strips at `x = ±5`, and soft glowing green floor wash.
- **As-Safa (`z = +10.5`) & Al-Marwa (`z = -130.5`)**: Sculpted dark Hijazi granite rock formations with natural fractured rock facets & textured rock shader, enclosed behind curved cream-marble & brushed-brass semicircular railings (`r = 8 m`), wide gentle marble ramps leading up, and gilded Qibla directional arrow plaques on the West wall (`x = -9.6`).
- **Budget**: ≤ 34,000 tris (`LOD0`), ≤ 14,000 tris (`LOD1`), ≤ 700 KB GLB.

## Acceptance Checks
1. Every individual script (`blender -b -P blender/env/<name>.py`) and `blender/env/build_all.py` exits 0 and outputs its GLB to `public/models/env/`.
2. All 8 GLBs stay within triangle and KB budgets (total environments ≤ 4.8 MB).
3. Visual inspection of every rendered preview PNG in `blender/previews/env_*.png` confirms realistic materials, crisp geometry, zero Z-fighting, exact landmark orientation (Kaaba door on NE, Black Stone on E, Hijr on NW, Yamani on S), and legible green lights in Mas'a.
4. World-space bounding boxes verified against `BOXES`, `BOUNDS`, `HOME_SPOTS`, `AIRPORT_SPOTS`, `PLANE_SPOTS`, `MAKKAH_SPOTS`, `collideMataf`, and `collideMasa`.

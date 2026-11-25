# 003 — Realistic Faceless Characters, Rigging & Animations

Status: Approved · Owner: Orchestrator (Gemini 4 Neon XHigh)

## Binding Religious & Art Rules
1. **Strictly smooth faceless heads**: NO eyes, NO orbital eye sockets, NO nose, NO mouth, NO eyebrows, NO eyelids, NO painted facial features whatsoever. The head is a clean, anatomically proportioned sculptural oval/cranium with smooth jaw and neck transition, paired only with realistic sculpted hair, beard (for older mentor), or hijab/shemagh headwear.
2. **Never depict the Prophet ﷺ or any Companion.**
3. **Realistic human proportions**: Adult head-to-height ratio **1:7.2 to 1:7.4** (natural shoulders, waist, limbs, anatomically shaped hands and sandals/shoes — NOT chibi, NOT clay capsules, NOT anime outlines).
4. **Realistic clothing**: Authentic draped white terry-cotton ihram (`izar` lower wrap with overlapping front pleat + `rida` upper wrap in both full-shoulder and diagonal `idtiba'` states), realistic everyday travel clothing, modest tailored abayas & draped hijabs for women, airline flight attendant uniform + hijab, airline counter agent uniform, and Makkah hotel/Haram guide attire.

## File Layout & Responsibilities

| Path | Responsibility |
|---|---|
| `blender/characters/__init__.py` | Package marker. |
| `blender/characters/rig.py` | Realistic 19-bone humanoid skeleton (`compute_landmarks`, `build_armature`) + smooth analytical skinning (`skin_body`, `skin_upper_garment`, `skin_izar_robe`, `skin_trousers`, `skin_headwear`, `skin_rigid`). Zero face bones. |
| `blender/characters/body.py` | Realistic anatomical base body generator (smooth faceless head, neck, sculpted torso/shoulders/clavicles, tapered arms & forearms, realistic articulated-silhouette hands with thumb + curved finger block, legs, ankles, bare feet for sandals & covered shoes). |
| `blender/characters/garments.py` | Realistic layered garment builders: (a) draped cotton `izar` + `rida_covered` + `rida_idtiba` (leaving right shoulder `-X` cleanly bare while wrapping diagonally under right armpit and over left `+X` shoulder with natural cloth folds); (b) casual travel shirt & trousers; (c) flight attendant modest long uniform dress/jacket & draped hijab; (d) Makkah hotel/Haram guide thobe/suit & shemagh/agal; (e) airline counter agent collared uniform shirt & trousers; (f) sculpted short hair & mentor's full neatly rounded grey beard. |
| `blender/characters/anim.py` | 24 fps seamless NLA clip generator for the 19-bone rig: `idle`, `walk`, `run` (raml / green-lights jog), `talk`, `gesture` (right hand raised toward Black Stone / Qibla), `pray` (standing → ruku' → standing → sujud prayer cycle). |
| `blender/characters/cast.py` | Character specs & builder orchestrating body + garments + materials + skinning + animations for `player`, `mentor`, `attendant`, `guide`, `agent`. |
| `blender/characters/crowd.py` | Low-poly realistic crowd archetypes builder exporting `public/models/characters/crowd.glb` for `InstancedMesh` rendering (standing & seated variants). |
| `blender/characters/build_all.py` | Standalone CLI entry point (`blender -b -P blender/characters/build_all.py [-- keys...]`) exporting all GLBs to `public/models/characters/`, printing budget stats, and rendering turnaround/pose preview PNGs to `blender/previews/chars_*.png`. |

## Skeleton Contract (19 Deform Bones)
Facing `-Y` in Blender (`+Z` up) → facing `+Z` in Three.js (`+Y` up). Origin `(0, 0, 0)` on the floor between the feet.
- Spine chain: `pelvis` → `spine_01` → `spine_02` → `neck` → `head`
- Left arm (`+X`): `clavicle_l` → `upperarm_l` → `lowerarm_l` → `hand_l`
- Right arm (`-X`): `clavicle_r` → `upperarm_r` → `lowerarm_r` → `hand_r`
- Left leg (`+X`): `thigh_l` → `calf_l` → `foot_l`
- Right leg (`-X`): `thigh_r` → `calf_r` → `foot_r`

## Exported Character GLBs & Mesh Toggle Contract

### 1. `public/models/characters/player.glb` (~1.76 m)
- **Skinned child mesh names** (kept as distinct objects parented to the armature so Three.js can toggle outfits & idtiba' instantaneously with zero reload):
  - `body_skin` — smooth faceless head, neck, torso, arms, hands, lower legs, feet (always visible)
  - `hair` — realistic dark brown short sculpted hair (always visible)
  - `outfit_street` — steel-blue collared travel shirt + charcoal tailored trousers + casual travel shoes
  - `outfit_ihram_izar` — wrapped white woven cotton lower ihram towel (waist to mid-shin) + comfortable slip-on sandals
  - `outfit_ihram_rida_covered` — draped white cotton upper ihram shawl covering both shoulders naturally
  - `outfit_ihram_rida_idtiba` — draped white cotton upper ihram shawl passing under right armpit (`-X`) and draped over left shoulder (`+X`), leaving right shoulder & upper arm bare
- **Clips (NLA track names)**: `idle`, `walk`, `run`, `talk`, `gesture`, `pray`
- **Budget**: ≤ 14,000 tris total across all outfit layers, ≤ 450 KB Draco+WebP GLB.

### 2. `public/models/characters/mentor.glb` (الحاج حسن, ~1.72 m)
- Warm weathered skin, slightly broader mature build, gentle posture, silver-grey sculpted hair + full neat silver-grey beard framing smooth faceless jaw.
- **Same exact skinned mesh names** as `player.glb` (`body_skin`, `hair`, `outfit_street`, `outfit_ihram_izar`, `outfit_ihram_rida_covered`, `outfit_ihram_rida_idtiba`), with warm sand/beige linen travel shirt + dark khaki trousers in `outfit_street`.
- **Clips**: `idle`, `walk`, `run`, `talk`, `gesture`, `pray`
- **Budget**: ≤ 14,000 tris total, ≤ 450 KB GLB.

### 3. `public/models/characters/attendant.glb` (~1.65 m)
- Modest burgundy airline uniform long dress & tailored blazer, cream collar accent, neatly draped burgundy/cream hijab framing smooth faceless head, low shoes.
- **Clips**: `idle`, `talk`
- **Budget**: ≤ 8,000 tris, ≤ 260 KB GLB.

### 4. `public/models/characters/guide.glb` (~1.75 m)
- Makkah hotel/Haram hospitality guide: crisp charcoal/navy hospitality jacket over white shirt (or dignified white Saudi thobe + dark vest + red-and-white checkered shemagh with black agal — let's use crisp hospitality navy blazer/thobe + subtle gold lapel badge & traditional Makkah hospitality look so he reads instantly in the hotel lobby).
- **Clips**: `idle`, `talk`
- **Budget**: ≤ 8,000 tris, ≤ 260 KB GLB.

### 5. `public/models/characters/agent.glb` (~1.74 m)
- Airport check-in counter staff: crisp navy airline uniform shirt, dark trousers, subtle badge/lanyard, smooth faceless head + short dark hair.
- **Clips**: `idle`, `talk`
- **Budget**: ≤ 7,500 tris, ≤ 240 KB GLB.

### 6. `public/models/characters/crowd.glb` (Instanced Crowd Archetypes, static meshes)
Each archetype is a realistic low-poly human figure (400–650 tris per archetype, smooth faceless head, natural arms & posture) split into 2 clean sub-meshes so Three.js `InstancedMesh` can tint skin tone and clothing independently via `setColorAt` with minimal draw calls:
- `crowd_ihram_idtiba_cloth` + `crowd_ihram_idtiba_skin` (man in izar + diagonal idtiba' rida, bare right shoulder `-X`)
- `crowd_ihram_covered_cloth` + `crowd_ihram_covered_skin` (man in izar + covered rida over both shoulders)
- `crowd_man_street_cloth` + `crowd_man_street_skin` (man in shirt + trousers, cloth color tinted per instance)
- `crowd_woman_abaya_cloth` + `crowd_woman_abaya_hijab` + `crowd_woman_abaya_skin` (woman in modest long flowing abaya + draped hijab + smooth faceless head)
- `crowd_seated_man_cloth` + `crowd_seated_man_skin` (seated airline passenger — bent hips/knees at airline seat height `y=0.55 m`, feet resting on floor `y=0`)
- `crowd_seated_woman_cloth` + `crowd_seated_woman_hijab` + `crowd_seated_woman_skin` (seated woman passenger in abaya & hijab)
- **Budget**: ≤ 4,500 tris across all 6 archetypes combined, ≤ 180 KB GLB.

## Acceptance Checks
1. `blender -b -P blender/characters/build_all.py` regenerates all 6 GLBs cleanly with exit code 0.
2. Visual check of rendered turnaround PNGs (`player`, `mentor`, `attendant`, `guide`, `agent`, `crowd`) confirms:
   - Realistic adult proportions (not stubby/chibi, not capsule-like).
   - **Zero** facial features on every single character.
   - `outfit_ihram_rida_idtiba` clearly uncovers the RIGHT shoulder (`-X`) and drapes naturally over the LEFT shoulder (`+X`).
   - `outfit_ihram_rida_covered` cleanly covers both shoulders with no skin poke-through.
   - `walk`, `run`, `gesture`, `pray` pose renders show clean joint deformation without torn vertices or clipped limbs.
3. All 6 GLBs pass budget thresholds and load cleanly in Three.js with named meshes and NLA clips matching the contract above.

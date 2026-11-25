# 002 — Blender Pipeline & Realistic PBR Asset Architecture

Status: Approved · Owner: Orchestrator (Gemini 4 Neon XHigh) · Target: Blender 5.2.2 LTS

## Overview
All 3D characters, props, and architectural environments for **«رحلة العمرة»** are generated procedurally in **Blender 5.2.2 LTS** using standalone, deterministic Python scripts modeled on the sister project `/var/www/html/old/3d-quranic/blender/`.

Unlike the sister project's cel-shaded/anime v3 pipeline, this project uses a **realistic PBR style**: realistic human proportions, physically based roughness/metalness, packed procedural WebP textures (marble, silk Kiswa, embroidered gold, wood, terrazzo, woven fabric, granite), baked geometric vertex AO, and **zero** inverted-hull toon outlines.

## Directory Layout & File Responsibilities

| Path | Responsibility |
|---|---|
| `blender/_bridge/bridge.py` | Live Blender scripting bridge (watcher timer executing jobs from `_bridge/in/` → `_bridge/out/`). |
| `blender/_bridge/bx.py` | CLI helper to submit a `.py` job to a running Blender GUI via `_bridge/`. |
| `blender/_bridge/cam.py` | Reusable viewport/render camera setup (`ShotCam`). |
| `blender/_bridge/shot.py` | Viewport screenshot helper. |
| `blender/lib/__init__.py` | Package init (`sys.dont_write_bytecode = True`). |
| `blender/lib/common.py` | Deterministic `reset_scene()`, `three_to_bl(tx, ty, tz)` coordinate converter, `srgb_to_linear()`, `make_pbr_material()`, `pack_image_webp()` / `pack_image_png()`, `bake_vertex_ao()`, `make_lod1()`, `uv_box_project()` / `uv_cylindrical()`, `export_glb()` (Draco-6 + WebP), `tri_count()`, and JSON budget reporter. |
| `blender/lib/textures.py` | NumPy procedural PBR texture generators packed directly into Blender images (zero external loose texture directories): veined Thassos marble, warm cream marble, black silk Kiswa with embroidered metallic gold Hizam & cartouches, woven cotton ihram terry cloth, woven abaya/cloth micro-grain, oak wood floorboards, plaster wall, Persian rug pattern, terrazzo floor, Hijazi granite rock, brushed brass/gold relief. |
| `blender/lib/preview.py` | Headless EEVEE Next studio preview renderer (3-point warm sunlight + sky world) writing verification PNGs into `blender/previews/`. |
| `blender/characters/*.py` | Character geometry, realistic 19-bone rig, NLA animations, crowd archetypes, and `build_all.py` (see [003-characters.md](003-characters.md)). |
| `blender/env/*.py` | One script per environment/landmark plus `build_all.py` (see [004-environments.md](004-environments.md)). |
| `blender/build_all.py` | Master entry point to regenerate every character and environment GLB from scratch. |
| `blender/previews/` | Rendered inspection PNGs (gitignored or kept small; not deployed to `public/`). |
| `public/models/characters/` | Exported rigged character GLBs (`player.glb`, `mentor.glb`, `attendant.glb`, `guide.glb`, `agent.glb`, `crowd.glb`). |
| `public/models/env/` | Exported environment GLBs (`home.glb`, `airport.glb`, `plane.glb`, `makkah.glb`, `kaaba.glb`, `maqam.glb`, `haram_mataf.glb`, `masa.glb`). |

## Coordinate Convention (Strict Contract)
- **Blender**: Right-handed, **+Z up**, characters face **-Y** (so character LEFT = `+X`, character RIGHT = `-X`).
- **glTF Export (`export_yup=True`)**: Maps Blender `(bx, by, bz)` → Three.js `(bx, bz, -by)`.
  - Characters facing `-Y` in Blender export facing `+Z` in Three.js, with origin `(0, 0, 0)` at ground between feet, character LEFT = `+X`, character RIGHT = `-X` (matching `src/game/people.js` and `Controller.jsx`).
  - Environments map any Three.js world coordinate `(tx, ty, tz)` into Blender via:
    ```python
    def three_to_bl(tx, ty, tz):
        return Vector((tx, -tz, ty))
    ```
  - Rotations around Three.js `+Y` map identically to rotations around Blender `+Z` (`rot_z = three_rot_y`).

## Material, Texture & Compression Budget
- **Shader**: `ShaderNodeBsdfPrincipled` only (no cel ramps, no emission hacks except explicit lamps/green markers/windows).
- **Textures**: Generated procedurally via `numpy` in `blender/lib/textures.py` and packed into `.glb` with `export_image_format='WEBP'`, `export_image_quality=82`.
  - Character cloth/skin detail textures: max `512×512`.
  - Hero architectural textures (Kiswa, Mataf marble, rug): max `1024×1024`.
  - Secondary environment textures (wood, plaster, terrazzo, rock): `512×512`.
- **Vertex AO**: Fast geometric concavity + ground-contact AO baked into vertex color attribute `Color` on static environment meshes where helpful (`export_vertex_color='ACTIVE'` or baked into base-color multiply).
- **Compression**: Draco mesh compression (`export_draco_mesh_compression_enable=True`, `export_draco_mesh_compression_level=6`, position quantization 14, normal 10, texcoord 12).
- **LODs**: Each heavy environment GLB exports clean `*_LOD0` (Normal tier) and `*_LOD1` (Lite tier, ~35–45% triangles via clean simplification or lighter instanced/architectural detail) child groups so the R3F loader toggles them based on `Q.name` without duplicating textures.
- **Total Size Budget**: All GLBs combined in `public/models/` should target **≤ 8 MB** compressed (ideally 3–6 MB) so phones download and PWA-precache rapidly.

## CLI Invocation
Every script must be directly runnable headless from the repository root:
```bash
blender -b -P blender/characters/build_all.py
blender -b -P blender/env/kaaba.py
blender -b -P blender/env/build_all.py
blender -b -P blender/build_all.py
```

## Acceptance Checks
1. `blender -b -P blender/lib/common.py` (smoke test) exits 0 with no missing imports.
2. Every script in `blender/characters/` and `blender/env/` runs cleanly from repo root with `blender -b -P <script>.py` and exits 0.
3. Every exported GLB has valid glTF 2.0 header (`glTF` magic), Draco extension (`KHR_draco_mesh_compression`), packed WebP textures (zero external `.png`/`.webp` links), and meets its triangle & KB budget in `blender/_report_*.json`.
4. Preview PNGs render cleanly in headless Blender (`BLENDER_EEVEE_NEXT` or `BLENDER_EEVEE` — detect available engine string dynamically in Blender 5.2.2) for visual inspection.

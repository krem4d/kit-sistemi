# AGENTS.md — Adaptx Otonom Kit

Guidance for AI agents (and humans) working in this repository. Read this first.

> The project is Turkish-facing: documentation, code comments, JSON keys, and PDF
> labels are in Turkish. Keep that convention — write new comments/strings in Turkish
> to match the surrounding code. This file is in English by request.

---

## 1. What this project does

Adaptx Otonom Kit is an **autonomous furniture-hardware counting pipeline**. Given
per-order 3D models (`.fbx`) of flat-pack furniture, it detects the drilled holes and
part geometry, derives how many of each hardware item (hinges, cam locks/"linco",
shelf pins, feet, handles, rails, etc.) the order needs, and produces per-order and
summary **PDF pick-lists** with quantities and weights.

Detection is **geometry-based**, not name-based: raw FBX parts are generically named
(`Object_N`), so everything is inferred from hole **volumes**, **distances**,
**directions**, and part **thickness**.

---

## 2. Architecture — two processes

Blender's bundled Python has no `matplotlib`, so the pipeline is split in two:

```
fbx/*.fbx ─▶ [Blender headless]  parca_sayim.py ─▶ jsons/<order>.json
                                                         │
             [system python + matplotlib] pdf_uret.py ◀─┘ ─▶ pdf/<order>.pdf + pdf/siparisler_ozet*.pdf
```

- **`parca_sayim.py`** runs inside Blender (`blender --background --python …`). It is the
  heavy stage: imports each FBX, runs the hole-detection boolean, applies all counting
  rules, writes one JSON per order to `jsons/`.
- **`pdf_uret.py`** runs under system Python 3 + matplotlib. It reads `jsons/*.json` and
  renders the PDFs.
- **`calistir.sh`** is the orchestrator: it runs the Blender stage, then the PDF stage.

### Run the whole pipeline
```bash
bash calistir.sh
```

### Run stages individually
```bash
blender --background --python parca_sayim.py   # fbx/ -> jsons/*.json
python3 pdf_uret.py                            # jsons/*.json -> pdf/
```

### Syntax-check without Blender/LibreOffice
```bash
python3 -m py_compile parca_sayim.py pdf_uret.py
```
`parca_sayim.py` cannot fully run outside Blender (imports `bpy`), so `py_compile` +
small standalone logic tests are the normal pre-flight checks.

---

## 3. Directory / file map

| Path | Role |
|------|------|
| `fbx/` | **Input.** One `.fbx` per order (order no. parsed from filename). |
| `jsons/` | **Intermediate.** One `<order>.json` per processed order (also the "already done" record). |
| `pdf/` | **Output.** `pdf/siparişler pdf/<order>.pdf` (per order) + `pdf/siparisler_ozet*.pdf` (summary, 14 orders/page). |
| `islem_gecmisi.json` | **Memory/manifest.** Processing order of orders (see §5). |
| `parca_sayim.py` | Main counting engine (Blender headless). |
| `pdf_uret.py` | PDF generator (system python + matplotlib). |
| `calistir.sh` | Orchestrator. |
| `parca_kurallari.md` | **Source of truth for counting rules** — read before touching detection logic. |
| `hacimler.md` | Reference hole/part volumes and their tolerances. |
| `Ağırlıklar.md` | Per-unit gram weights (feeds `WEIGHTS`). |
| `Eksikler.md` | Deferred features / open questions (mostly need input from "Mert"). |
| `delikbulma.py` | Original standalone detector; **reference only**, do not depend on it at runtime (helpers were copied into `parca_sayim.py`). |
| `hacim_bul.py`, `kalinlik_bul.py`, `kulp_mesafe_bul.py`, `linco_mesafe_bul.py`, `linco_uzun_pim_teshis.py` | **Diagnostic tools** run interactively in Blender (see §7). Not part of the pipeline. |
| `*_raporu.txt` | Text outputs of the diagnostic tools. |
| `PLAN.md`, `PROGRESS.md` | Phase plan and progress notes. |

---

## 4. Detection engine — how it works

### 4a. Prep (`prep_import`)
`read_factory_settings(use_empty=True)` → `import_scene.fbx` → delete junk cameras
(`Front/Perspective/Right/Top`) → un-parent every child of the `Default` empty
(preserving world matrices) → delete `Default`. Order number is parsed from the filename
with `re.search(r'(\d{4,}(?:-\d+)?)', ...)` (e.g. `9257-1.fbx` → `9257-1`).

### 4b. Hole detection (`execute_double_boolean`) — the core trick
For each mesh part, cavities (drilled holes) are extracted with a **double boolean**:
1. `outer_prism` = part's local bounding box scaled ×**1.002**.
2. `DIFFERENCE` (EXACT solver) outer_prism − original part → keeps only the shell +
   cavities.
3. `INTERSECT` with `inner_prism` (×**0.998**) → isolates the internal cavities.
4. `separate(LOOSE)` → each cavity becomes its own object; `bmesh.calc_volume()` gives
   its volume.

Each cavity's volume is matched to a category (`match_category`) within `TOLERANCE`.

### 4c. Volume categories (`CATEGORIES`, model units = mm³)
`linco`=9680, `pim`=936 (linco dübel hole), `ahsapcivisi`=14.57 (wood screw),
`rafpimi`=234, `modulbaglanti`=351.35, `menteseTabani`=11454.0131. `TOLERANCE`=0.05 (±5%).

### 4d. Calibration (critical)
**1 Blender/model unit = 1000 mm.** Anchored on the handle ("kulp") hole spacing:
`0.192` model units ↔ `192 mm`. Distance-based rules use either model units directly
(e.g. `LONG_LINCO_MESAFE=0.043`) or `RAY_SCALE_MM=1000` to convert to mm.

### 4e. Derivation rules (summary — full detail in `parca_kurallari.md`)
- **Menteşe Tabanı** = count of `menteseTabani` holes.
- **Frenli Menteşe** = number of *parts* containing ≥1 menteşe tabanı; **Frensiz** =
  total menteşe tabanı − frenli.
- **Kulp** = per-part `modulbaglanti` holes paired at ~192 mm (`detect_kulp_pairs`);
  **Kulp Vidası** = 2×kulp. Unpaired `modulbaglanti` holes fall through to…
- **Modülleri Birbirine Bağlama** = A–B `modulbaglanti` pairs within 0.2 (`pair_count`).
- **Raf Pimi** = `rafpimi` holes // 3.
- **Linco Gövde = Linco Kapak = Minifix** = `linco` hole count.
  **Linco Dübel** = linco − 2×(uzun linco pimi).
- **Uzun Linco Pimi** (long L-module pin) — see §4f.
- **Ayarlı Ayak** = parts with **exactly 4** wood-screw holes (after rays removed).
  **Allen** = 1 if ayak≥1 else 0. **Tıpa** = ayak.
- **Ray Seti** = wood-screw holes forming a collinear rail spacing pattern
  (`detect_rays`, `RAY_GAPS`); 2 same-length rails = 1 set.
- **Ağaç Vidası** = (non-ray wood-screw holes) + 4 × L bağlantı seti.
- **Askılık Flanşı** = equilateral (~60°, ±2% sides) triangles of wood-screw holes
  (`count_equilateral_flanges`); **Askılık Borusu** = flanşı // 2.
- **L Bağlantı Seti** = fixed **2** per order (`L_BAGLANTI_ADET`, temporary).
- **Arkalık Çivisi** = perimeter nails of back panels (parts thinner than
  `ARKALIK_MAX_KALINLIK`=8 mm), spaced `CIVI_ARALIK_MM`=150 mm.
- **Gram** columns = quantity × `WEIGHTS[...]` (see `Ağırlıklar.md`).

### 4f. Uzun Linco Pimi (long L-module pin) — the trickiest rule
When two **different** abutting modules have back-to-back `linco` body holes, a single
long pin replaces the two normal linco dübels. A candidate pair (holes `a`, `b` in
different parts, `conn = b − a`, `conn_hat` normalized) is valid iff **all** hold:
1. **distance**: `LONG_LINCO_MESAFE` (0.043) ±`LONG_LINCO_TOL` (25%) → [0.032, 0.054].
2. **A faces B**: `dir_A · conn_hat >= LONG_LINCO_ALIGN_MIN` (0.9).
3. **B faces A**: `dir_B · conn_hat <= −LONG_LINCO_ALIGN_MIN`.
4. **connecting line is axis-aligned (multiple of 90°)**: `max|conn_hat component| >=
   LONG_LINCO_AXIS_MIN` (0.985 ≈ cos 10°).

`dir_*` is the **signed** drilling direction from `hole_signed_direction()`: cast 6
axis rays from the cavity center at the panel; the non-hitting direction is the open
(drilling) end. Greedy nearest-first matching, each hole used once. Each valid pair =
1 pin and removes 2 linco dübels. Checks 2–4 exist because distance-only (and even
*unsigned* direction) produced false positives — an irrelevant bridge between two real
pairs, and same-direction pairs. If false positives persist, tighten `ALIGN_MIN`
(→0.95) or `AXIS_MIN` (→0.995).

---

## 5. Memory / incremental processing (do-not-redo)

The pipeline **skips orders it has already produced** so re-running only processes new
FBX files, and the summary **appends** new orders at the end.

- **`jsons/<order>.json` existence = "already processed".** `parca_sayim.py` skips any
  FBX whose JSON already exists (the expensive Blender stage is not re-run).
- **`islem_gecmisi.json`** (`{"siralama": [order, …]}`) records the **processing order**.
  Existing JSONs are seeded into it sorted; genuinely new orders are appended to the
  **end**. Both scripts read/write it and self-heal (any JSON missing from the manifest
  is appended).
- **`pdf_uret.py`** renders per-order PDFs only for orders **missing** a PDF, but always
  **regenerates the summary** in manifest order (so a newly added order lands at the end
  of `siparisler_ozet*.pdf`, on page 2+ as needed). Stale `siparisler_ozet*.pdf` are
  cleared before regen.

**To force a full re-run:** delete the relevant `jsons/<order>.json` (and/or the
per-order PDF), or delete `islem_gecmisi.json` to reset ordering.

---

## 5b. Deployment as a service (Docker)

The pipeline can run headless as a container service that polls `fbx/` every
`POLL_INTERVAL` seconds (default 300 = 5 min) and processes new orders automatically.

- **`Dockerfile`** — Debian slim + system Python/matplotlib + official Blender tarball
  (version via `BLENDER_MAJOR`/`BLENDER_VERSION` build-args).
- **`docker/entrypoint.sh`** — poll loop: runs `calistir.sh` only when
  `docker/yeni_var_mi.py` reports an FBX without a matching JSON.
- **`docker-compose.yml`** — bind-mounts host `./data` → container `/data`.
- **`ADAPTX_BASE`** env var (default `/data`) is the data root; both `parca_sayim.py`
  and `pdf_uret.py` honor it (falling back to `PROJE_DIZINI`/`__file__` off-container),
  so paths are static and portable across machines.
- Full Proxmox CT / Docker instructions: **`DOCKER.md`**.

Data layout on the host mount: `data/fbx` (input), `data/jsons` + `data/islem_gecmisi.json`
(state), `data/pdf` (output). Code lives in `/app` inside the image; data is never baked in
(see `.dockerignore`).

## 6. Conventions & gotchas

- **Language:** new code comments and user-visible strings in **Turkish**. Match the
  existing terse, section-headed comment style (`# ── … ──`).
- **Zero = blank:** `pdf_uret.fmt()` renders `0`/`None` as an **empty cell** (user
  request). Don't reintroduce `"0"` or `"—"` for zero quantities.
- **Path resolution:** `parca_sayim.py` hard-codes `PROJE_DIZINI` first (Blender's
  `__file__` can be unreliable in the text editor), then falls back to `__file__`/cwd.
  If the project moves, update `PROJE_DIZINI`.
- **Don't edit `delikbulma.py`** expecting it to affect the pipeline — its helpers were
  copied into `parca_sayim.py`. Keep the copies in sync manually if you change shared logic.
- **`.fbx` and `.blend` are git-ignored-ish / large** — `.claudeignore` excludes the big
  blend files and stale reports. This is **not a git repo** (no VCS); don't assume
  `git` commands work.
- **LibreOffice locks:** if a summary PDF is open (`.~lock.*` present), regeneration may
  fail to overwrite it. Close the viewer before running the pipeline.
- **Performance:** EXACT boolean per part costs seconds; large orders take a while. The
  skip-already-processed memory (§5) is what keeps re-runs cheap.
- **Cross-part linco holes** carry `(world_center, signed_direction)` tuples; keep that
  shape if you touch `count_order` → `detect_long_linco_pins`.

---

## 7. Diagnostic tools (interactive, in Blender GUI)

These are **not** part of the pipeline. Open the model in Blender, select the relevant
part(s), run the script from the Text editor; each writes a `*_raporu.txt` and/or places
named Empties for visual inspection. Established workflow: **write a diagnostic → user
runs it in the GUI → analyze the report → then build/adjust the pipeline rule.**

- `hacim_bul.py` — measure the volume of selected hole/part (to fill `hacimler.md`).
- `kalinlik_bul.py` — report a part's min edge (MDF thickness; back-panel threshold).
- `kulp_mesafe_bul.py` — distances between `modulbaglanti` holes (handle spacing).
- `linco_mesafe_bul.py` — with **exactly 2 parts selected**, cross-part linco hole
  distances (source of the ~43 mm long-pin threshold). Coordinates are model units
  (×1000 = mm).
- `linco_uzun_pim_teshis.py` — scans the whole scene, places named Empties at long-pin
  candidates tagged `MATCH` / `near` (distance) / `axis_bad` (not axis-aligned) /
  `face_bad` (not facing) for visual verification.
- `collider_kutusu_goster.py` — for selected parts, runs the pipeline's exact
  `get_perfect_local_bounds` bounding-box calc and drops a real (wireframe, ×1.0 scale)
  mesh box named `ColliderBox_<part>` into the scene at the object's transform, so the
  hole-detection collider box can be visually checked against the actual part geometry.

---

## 8. Deferred / needs external input (see `Eksikler.md`)

- **L Bağlantı Seti / Vidası / Dübeli** — currently a hard-coded 2; real detection needs
  module identification and a decision (with "Mert").
- **Kulp** — some models have handles without a kulp dummy; detection will change.
- **Color of colored parts** — needs Mert to embed texture info in the FBX.
- **Ray sets** — partially done; Mert to relate rail lengths to screw spacings.
- **Renk/kontrol flags** (white/grey linco, tıpa colors, EVET/HAYIR checklist items) —
  deferred.

When picking up deferred work, read `Eksikler.md` and `parca_kurallari.md` together, and
prefer the diagnostic-first workflow in §7 before hardcoding a new rule.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Read `AGENTS.md` first — it is the primary, detailed reference for this repo** (architecture,
detection engine internals, derivation rules, memory/incremental-processing model, deployment,
conventions, deferred work). This file is a short pointer plus a few things not in AGENTS.md.

> The project is Turkish-facing: documentation, code comments, JSON keys, and PDF labels are in
> Turkish. Match that convention in new code/comments. This file is in English by request (per
> AGENTS.md's own convention).

## What this project does

Adaptx Otonom Kit is an autonomous furniture-hardware counting pipeline. It reads per-order `.fbx`
3D models of flat-pack furniture, detects drilled holes/geometry (not part names), derives hardware
quantities (hinges, cam locks, shelf pins, feet, handles, rails, etc.), and produces PDF pick-lists.

## Common commands

```bash
bash calistir.sh                                # full pipeline: fbx/ -> jsons/ -> pdf/
blender --background --python parca_sayim.py    # stage 1 only: fbx/ -> jsons/*.json (needs Blender's bpy)
python3 pdf_uret.py                             # stage 2 only: jsons/*.json -> pdf/
python3 -m py_compile parca_sayim.py pdf_uret.py panel.py  # syntax check (works without Blender)
```

There is no test suite. Since `parca_sayim.py` imports `bpy` and only runs inside Blender,
`py_compile` plus the interactive diagnostic scripts (AGENTS.md §7) are the normal pre-flight
checks — there's no way to unit-test the detection logic outside Blender.

Web panel (read-only monitoring/checklist UI, stdlib-only, no pip deps):
```bash
python3 -m py_compile panel.py
python3 panel.py            # serves on :8080 (see PANEL.md for env vars, deployment)
```

## Architecture in one paragraph

Two-process pipeline because Blender's bundled Python lacks `matplotlib`: `parca_sayim.py` runs
headless inside Blender, doing FBX import, a double-boolean hole-detection trick per part, and
volume/distance-based rule derivation, writing one JSON per order to `jsons/`. `pdf_uret.py` runs
under system Python + matplotlib, reading those JSONs and rendering per-order and summary PDFs.
`calistir.sh` runs both stages in sequence. Both scripts skip orders already processed (JSON
existence = "done") and track processing order in `islem_gecmisi.json`, so re-runs only touch new
orders — see AGENTS.md §5 for the exact incremental-processing contract before changing either
script's I/O behavior.

`panel.py` is a separate, read-only stdlib web server (no Flask/pip) that visualizes pipeline state
and a per-order hardware checklist; it never writes to the pipeline's own data files. See `PANEL.md`
for its checklist model, theming, and Drive-video-streaming details.

## Key docs map (don't duplicate these, read them)

| File | Read when... |
|------|--------------|
| `AGENTS.md` | Always — full architecture, detection engine, all derivation rules, gotchas. |
| `parca_kurallari.md` | Touching any counting/derivation rule — source of truth. |
| `hacimler.md` | Working with hole-volume categories/tolerances. |
| `Ağırlıklar.md` | Working with per-unit weights (`WEIGHTS`). |
| `Eksikler.md` | Picking up deferred/open-question work. |
| `PANEL.md` | Working on `panel.py` (checklist model, theming, video streaming, systemd). |
| `DOCKER.md` | Docker/Proxmox deployment. |
| `SERVIS.md` | Native systemd (Docker-less) deployment. |

## Gotchas worth repeating

- `delikbulma.py` is reference-only; its helpers were copied into `parca_sayim.py` and must be kept
  in sync manually — editing `delikbulma.py` has no effect on the pipeline.
- `parca_sayim.py` hard-codes `PROJE_DIZINI` first (Blender's `__file__` is unreliable in its text
  editor); update it if the project moves.
- `pdf_uret.fmt()` renders `0`/`None` as an empty cell by design — don't reintroduce `"0"`/`"—"`.
- Diagnostic scripts (`hacim_bul.py`, `kalinlik_bul.py`, `kulp_mesafe_bul.py`, `linco_mesafe_bul.py`,
  `linco_uzun_pim_teshis.py`) are interactive-only (run inside Blender's GUI text editor), not part
  of the automated pipeline.

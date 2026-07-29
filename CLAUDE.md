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
- All scripts resolve their base directory dynamically (`ADAPTX_BASE` env var → `__file__`'s
  directory → open `.blend`'s directory → cwd), no hard-coded path; the whole project can be
  copied to a different location without edits.
- `pdf_uret.fmt()` renders `0`/`None` as an empty cell by design — don't reintroduce `"0"`/`"—"`.
- Diagnostic scripts all live in `test_scriptleri/` (moved out of the project root 2026-07-29).
  They are interactive-only (run inside Blender's GUI) and not part of the automated pipeline.
  **Never paste them into Blender's text editor** — that freezes a stale copy inside the `.blend`
  and later edits to the `.py` silently stop taking effect (this is exactly what happened to the
  report-writing fix). Run them via `test_scriptleri/BLENDER_CALISTIR.py`, which is opened from
  disk (Text Editor > Open) and `exec`s the chosen tool with a real `__file__`.
  Reports always land in `test_scriptleri/ciktilar/`; the resolved output path is printed on every
  run. `test_scriptleri/olcumler/` holds the archived measurements that certain constants in
  `parca_sayim.py` cite as evidence — those are never overwritten by a run.
- **Exception to the "no hard-coded path" rule:** the 7 measurement scripts in `test_scriptleri/`
  each carry a `SABIT_CIKTI_DIZINI` constant near the top. When a script is pasted into the text
  editor of an *unsaved* blend, Blender sets `__file__` to `/Text` and `bpy.data.filepath` to `""`,
  so no dynamic resolution is possible at all — and testing without saving is the normal workflow
  here. Dynamic resolution still runs first (env var → `__file__` → blend dir), so a moved project
  keeps working when launched from disk; the constant only catches the unresolvable case. Update
  those 7 lines if the project moves. The pipeline scripts stay fully portable — do not add
  hard-coded paths to `parca_sayim.py`, `pdf_uret.py`, or `panel.py`, which must run in Docker.

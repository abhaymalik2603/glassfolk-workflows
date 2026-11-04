# Glassfolk before/after workflow

Drop a batch of window-cleaning photos into one folder. This tool pairs each **before** with its **after** shot and exports square side-by-side composites (white frame, center gutter, **BEFORE** / **AFTER** labels) as **`.jpg`** files.

## Quick start (Windows)

1. Put all source photos in a folder (for example `C:\Photos\job-123`).
2. From this repo folder, run:

```powershell
.\run-before-after.ps1 "C:\Photos\job-123"
```

Composites are written to `C:\Photos\job-123\output\*.jpg`.

Optional output folder:

```powershell
.\run-before-after.ps1 "C:\Photos\job-123" -OutputFolder "C:\Photos\job-123\exports"
```

## How pairing works

1. **Filename hints** — Pairs photos that share the same base name after stripping tokens like `before`, `after`, `pre`, `post`, `dirty`, `clean` (underscores and hyphens supported).
2. **Scene similarity** — Remaining photos are paired when their perceptual hashes are close (same framing, different dirt/clean state).
3. **Before vs after** — Uses filename role when present; otherwise the softer (less sharp) image is treated as **before**.

Tip: naming like `patio_before.jpg` and `patio_after.jpg` is the most reliable.

## Python CLI

```powershell
cd c:\Users\abhay\dev\glassfolk-workflows
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m before_after "C:\Photos\job-123" -o "C:\Photos\job-123\output"
```

Options: `--similarity`, `--size` (default 2048), `--quality` (default 92).

## Input / output

- **Input:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.heic` in the chosen folder (not recursive).
- **Output:** `.jpg` only, optimized for social posts.

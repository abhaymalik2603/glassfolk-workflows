# Glassfolk before/after

Two photos in → one branded side-by-side **JPG** out.

## Web tool

```powershell
cd c:\Users\abhay\dev\glassfolk-workflows
.\run-web.ps1
```

Open **http://127.0.0.1:8787**

1. Add **Photo 1** and **Photo 2** (click or drag).
2. Leave **Auto-detect** on (softer/dirtier → BEFORE on the left), or turn off to force order.
3. Use **⇄** to swap if needed.
4. Click **Create JPG** → downloads `before_after.jpg`.

## Command line (two files)

```powershell
.\.venv\Scripts\python -m before_after "C:\path\before.heic" "C:\path\after.heic" -o "C:\path\output.jpg"
```

Force order (no auto-detect):

```powershell
.\.venv\Scripts\python -m before_after photo1.jpg photo2.jpg -o out.jpg --no-auto
```

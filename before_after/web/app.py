from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError

from before_after.images import is_image_filename, load_rgb
from before_after.two_photo import composite_two

logger = logging.getLogger("uvicorn.error")

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Glassfolk Before/After", version="2.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/composite")
async def create_composite(
    photo_one: UploadFile = File(...),
    photo_two: UploadFile = File(...),
    auto_detect: bool = Form(True),
    canvas_size: int = Form(2048),
    jpeg_quality: int = Form(92),
) -> Response:
    uploads = [photo_one, photo_two]
    blobs: list[bytes] = []

    for upload in uploads:
        if not upload.filename or not is_image_filename(upload.filename):
            raise HTTPException(status_code=400, detail="Upload two images (JPG, PNG, HEIC, WEBP).")
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"Could not read {upload.filename}.")
        try:
            load_rgb(data)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning("Decode failed %s: %s", upload.filename, exc)
            raise HTTPException(
                status_code=400,
                detail=f"Could not open {upload.filename}. Try exporting as JPG.",
            ) from exc
        blobs.append(data)

    try:
        jpg = composite_two(
            blobs[0],
            blobs[1],
            auto_detect=auto_detect,
            canvas_size=canvas_size,
            jpeg_quality=jpeg_quality,
        )
    except Exception as exc:
        logger.exception("Composite failed")
        raise HTTPException(status_code=500, detail=f"Could not build image: {exc}") from exc

    return Response(
        content=jpg,
        media_type="image/jpeg",
        headers={"Content-Disposition": 'attachment; filename="before_after.jpg"'},
    )

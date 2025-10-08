from __future__ import annotations
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from pypdf import PdfReader
from mutagen import File as MutagenFile

def cheap_meta_peek(path: Path) -> Tuple[Optional[str], float, str]:
    ext = path.suffix.lower()
    if ext in {".jpg",".jpeg",".png",".heic"}:
        try:
            with Image.open(path) as im:
                exif = im.getexif()
                if exif: return ("photos_by_date", 0.8, "meta:exif")
        except Exception:
            pass
    if ext == ".pdf":
        try:
            r = PdfReader(str(path))
            info = r.metadata
            if info and (info.title or info.producer or info.creator):
                return ("receipts_pdf", 0.76, "meta:pdfinfo")
        except Exception:
            pass
    if ext in {".mp3",".m4a",".flac",".mp4",".mkv",".mov"}:
        try:
            mf = MutagenFile(str(path))
            if mf and mf.tags: return ("media_by_tag", 0.8, "meta:id3/mp4")
        except Exception:
            pass
    return (None, 0.0, "meta:none")

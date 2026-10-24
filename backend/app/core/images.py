"""Validate bounded, embedded raster evidence without fetching remote URLs."""
import base64
import binascii
import io
import warnings
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_PIXELS = 20_000_000
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}

def image_metadata(value: str):
    header, encoded = value.split(",", 1)
    mime = header.removeprefix("data:").removesuffix(";base64")
    return mime, base64.b64decode(encoded, validate=True)

def validate_image(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 4 * ((MAX_IMAGE_BYTES + 2) // 3) + 64:
        raise ValueError("Photo must be JPEG, PNG or WebP, up to 3 MB")
    try:
        header = value.split(",", 1)[0]
        mime, data = image_metadata(value)
        if header != f"data:{mime};base64" or mime not in FORMATS or not data or len(data) > MAX_IMAGE_BYTES:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as picture:
                if picture.format != FORMATS[mime] or picture.width * picture.height > MAX_PIXELS or getattr(picture, "n_frames", 1) > 1:
                    raise ValueError()
                picture.verify()
            with Image.open(io.BytesIO(data)) as picture:
                picture.load()
    except (ValueError, binascii.Error, OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("Upload a valid, non-animated JPEG, PNG or WebP photo up to 3 MB and 20 megapixels") from None
    return value

def evidence_values(value, prefix):
    mime, data = image_metadata(value)
    extension = {"image/png":"png", "image/jpeg":"jpg", "image/webp":"webp"}[mime]
    return {"file_url":value,"file_name":f"{prefix}.{extension}","mime_type":mime,"file_size_bytes":len(data)}

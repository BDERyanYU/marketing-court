"""Validate bounded raster uploads; generated names never depend on upload paths."""

import hashlib
import io
import warnings

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000


def inspect_image(content: bytes, content_type: str | None):
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "请上传不超过 10 MB 的 PNG/JPG 图片。")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in ("PNG", "JPEG"):
                    raise HTTPException(415, "仅支持真实的 PNG/JPG 图片。")
                expected = "image/png" if image.format == "PNG" else "image/jpeg"
                if content_type != expected:
                    raise HTTPException(415, "文件类型与图片内容不一致。")
                width, height = image.size
                if width * height > MAX_PIXELS or min(width, height) < 32:
                    raise HTTPException(413, "图片应至少为 32×32，且不超过 2000 万像素。")
                image.verify()
        return width, height, ".png" if expected == "image/png" else ".jpg", hashlib.sha256(content).hexdigest()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(415, "图片无法解码，请使用完整的 PNG/JPG 文件。") from None

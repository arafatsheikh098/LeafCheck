"""F5: input image validation.

Content-based checks (NOT just file extension) before the bytes are ever
passed to PIL. Returns a `ValidatedImage` containing an open RGB PIL
image, or raises a `ValidationError` with a human-readable reason.

Rules (F5.AC1, G4):
  - max upload 5 MB
  - allowed formats: JPEG, PNG, WebP (BMP/GIF/TIFF rejected)
  - max pixel count 50_000_000 (decompression-bomb guard)
  - empty upload rejected
  - non-image bytes rejected
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_PIXELS = 50_000_000  # ~ 7000x7000


class ValidationError(ValueError):
    """Raised when an uploaded image fails content-based validation.

    The `reason` attribute is short, user-facing English; the message
    attribute is the same (for HTTP error rendering).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ValidatedImage:
    """A successfully-decoded image ready for preprocessing.

    `image` is always an RGB PIL image, with EXIF rotation applied
    (F5.AC1: "EXIF-rotated JPEG" should not require a manual rotation).
    """

    image: Image.Image
    original_format: str  # e.g. "JPEG", "PNG", "WEBP"


def _sniff_format(head: bytes) -> str | None:
    """Return a short name for the image format detected from the magic bytes."""
    if len(head) < 12:
        return None
    # JPEG: FF D8 FF
    if head[:3] == b"\xff\xd8\xff":
        return "JPEG"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    # WebP: "RIFF" .... "WEBP"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "WEBP"
    return None


def validate_image_bytes(data: bytes) -> ValidatedImage:
    """Validate raw upload bytes and return a ready-to-preprocess PIL image.

    Raises `ValidationError` on any rejection (empty, too big, wrong format,
    corrupt, too many pixels).
    """
    if not data:
        raise ValidationError("empty upload")

    if len(data) > MAX_UPLOAD_BYTES:
        raise ValidationError(f"file is {len(data) / (1024 * 1024):.1f} MB; max is 5 MB")

    fmt = _sniff_format(data[:12])
    if fmt is None:
        raise ValidationError("not a JPEG, PNG, or WebP image")

    # PIL's open() also enforces a max-pixels guard but only at
    # Image.DecompressionBombWarning level; we want a hard error before
    # the bytes are decoded. We do this by lowering PIL's
    # MAX_IMAGE_PIXELS env-var-equivalent (an int attribute on the
    # Image module) for the duration of this call.
    prev_max = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(BytesIO(data))
        img.load()  # forces full decode now so we fail early on truncated files
    except Image.DecompressionBombError as exc:
        raise ValidationError(f"image is too large (pixel count cap is {MAX_PIXELS})") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(f"corrupt or unreadable image: {exc}") from exc
    finally:
        Image.MAX_IMAGE_PIXELS = prev_max

    if img.width * img.height > MAX_PIXELS:
        raise ValidationError(f"image is {img.width}x{img.height}; pixel count cap is {MAX_PIXELS}")

    # Apply EXIF rotation (phone photos are physically upright but their
    # pixels are sideways) and convert to RGB. (F5.AC1: RGBA PNG, grayscale.)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    return ValidatedImage(image=img, original_format=fmt)

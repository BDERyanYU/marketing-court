"""Download OCR models and validate real text and coordinates on the sample."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.ocr import PaddleOCRService


if __name__ == "__main__":
    anchors = PaddleOCRService().extract(ROOT / "examples" / "eco-bottle.png", 1000, 1200)
    assert any("Eco-Friendly" in a.text for a in anchors), "Sample headline was not recognized"
    assert all(0 <= value <= 1 for a in anchors for point in a.polygon for value in point)
    print("OCR ready. Sample headline recognized; normalized coordinates validated.")

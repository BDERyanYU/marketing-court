"""Lazy PaddleOCR adapter; no model coordinates are invented."""

import math
import os
import logging
from pathlib import Path
from threading import Lock

from ..core.llm import ModelError
from ..core.store import new_id
from ..models.review import TextAnchor

logger = logging.getLogger(__name__)


class PaddleOCRService:
    def __init__(self):
        self._engine = None
        self._lock = Lock()

    def extract(self, path: Path, width: int, height: int) -> list[TextAnchor]:
        with self._lock:
            try:
                if self._engine is None:
                    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
                    from paddleocr import PaddleOCR
                    self._engine = PaddleOCR(lang="en", use_doc_orientation_classify=False,
                                             use_doc_unwarping=False, use_textline_orientation=False,
                                             enable_mkldnn=False)
                results = list(self._engine.predict(str(path)))
                anchors = []
                for result in results:
                    for text, score, polygon in zip(result["rec_texts"], result["rec_scores"], result["rec_polys"]):
                        text, score = text.strip(), float(score)
                        if not text or not math.isfinite(score) or score < 0.5:
                            continue
                        points = [(float(x) / width, float(y) / height) for x, y in polygon]
                        if len(points) != 4 or any(not math.isfinite(v) or v < 0 or v > 1 for p in points for v in p):
                            continue
                        anchors.append(TextAnchor(anchor_id=new_id("anchor"), text=text, polygon=points,
                                                  score=score, method="paddleocr"))
                if not anchors:
                    raise ModelError("未识别到可靠文字，请换一张更清晰的图片。")
                return anchors
            except ImportError:
                raise ModelError("OCR 依赖尚未安装。请先执行 uv sync --extra ocr 并准备 PaddleOCR 模型。") from None
            except ModelError:
                raise
            except Exception as error:
                logger.error("OCR failed: %s", type(error).__name__)
                raise ModelError("OCR 解析失败，请检查 PaddleOCR 安装与模型下载后重试。") from None

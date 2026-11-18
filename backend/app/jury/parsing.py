from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_DOCUMENT_CHARS = 48_000
MAX_PDF_PAGES = 60


class ReportError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def read_report(filename: str, data: bytes) -> str:
    if len(data) > MAX_FILE_BYTES:
        raise ReportError("报告超过 8 MB。", 413)
    extension = Path(filename).suffix.lower()
    readers = {
        ".txt": lambda body: body.decode("utf-8-sig"),
        ".md": lambda body: body.decode("utf-8-sig"),
        ".pdf": read_pdf,
        ".docx": read_docx,
    }
    if extension not in readers:
        raise ReportError("支持 UTF-8 文本、Markdown、文字 PDF 和 DOCX。", 415)
    try:
        text = readers[extension](data).strip()
    except ReportError:
        raise
    except (KeyError, OSError, ValueError):
        raise ReportError("无法读取报告。请确认文件格式和内容完整。") from None
    if not text:
        raise ReportError("报告没有可提取文字。扫描件请先转成可复制文本。")
    if len(text) > MAX_DOCUMENT_CHARS:
        raise ReportError("正文超过 48,000 字符，请上传其中包含客群分析的章节。", 413)
    return text


def read_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ReportError("请上传无需密码即可读取的 PDF。")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ReportError("PDF 超过 60 页，请选择客群调研章节。", 413)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except PyPdfError:
        raise ReportError("无法读取 PDF。请检查文件是否完整。") from None


def read_docx(data: bytes) -> str:
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError
    from docx.text.paragraph import Paragraph
    from lxml.etree import XMLSyntaxError
    from zipfile import BadZipFile

    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 32 * 1024 * 1024:
                raise ReportError("DOCX 解压后超过处理上限。", 413)
        document = Document(BytesIO(data))
        blocks = []
        for item in document.iter_inner_content():
            if isinstance(item, Paragraph):
                blocks.append(item.text)
            else:
                for row in item.rows:
                    blocks.append("\t".join(cell.text for cell in row.cells))
        return "\n".join(blocks)
    except (BadZipFile, PackageNotFoundError, XMLSyntaxError):
        raise ReportError("无法读取 DOCX。请检查文件是否完整。") from None

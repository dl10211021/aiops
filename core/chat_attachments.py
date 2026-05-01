from __future__ import annotations

import base64
import io
import mimetypes
import os
import re
import zipfile
import xml.etree.ElementTree as ET


CHAT_ATTACHMENT_MAX_COUNT = 8
CHAT_ATTACHMENT_MAX_SIZE = 10 * 1024 * 1024
CHAT_IMAGE_MAX_DATA_URL_CHARS = 8 * 1024 * 1024
CHAT_IMAGE_DATA_URL_RE = re.compile(
    r"^data:image/(png|jpeg|jpg|gif|webp|bmp);base64,([A-Za-z0-9+/=\r\n]+)$",
    re.IGNORECASE,
)


class ChatAttachmentError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def optional_non_negative_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def normalize_sheet_names(value) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value[:5]:
        name = str(item or "").strip()
        if name:
            names.append(name[:80])
    return names


def normalize_chat_attachments(attachments: list[dict]) -> list[dict]:
    if len(attachments or []) > CHAT_ATTACHMENT_MAX_COUNT:
        raise ValueError(f"单次消息最多携带 {CHAT_ATTACHMENT_MAX_COUNT} 个附件。")

    normalized: list[dict] = []
    for raw in attachments or []:
        if not isinstance(raw, dict):
            raise ValueError("附件元数据格式无效。")

        filename = os.path.basename(str(raw.get("filename") or "attachment")).strip()
        if not filename:
            filename = "attachment"
        filename = filename[:180]

        ext = str(raw.get("ext") or os.path.splitext(filename)[1] or "").lower()[:24]
        content_type = str(raw.get("content_type") or "").lower()[:100]
        kind = str(raw.get("kind") or "document").lower()
        if kind not in {"document", "image"}:
            kind = "image" if content_type.startswith("image/") else "document"

        try:
            size = int(raw.get("size") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"附件 {filename} 的大小无效。") from None
        if size < 0 or size > CHAT_ATTACHMENT_MAX_SIZE:
            raise ValueError(f"附件 {filename} 超过 10MB 限制。")

        item = {
            "filename": filename,
            "ext": ext,
            "size": size,
            "content_type": content_type,
            "kind": kind,
            "rows": optional_non_negative_int(raw.get("rows")),
            "pages": optional_non_negative_int(raw.get("pages")),
            "sheets": normalize_sheet_names(raw.get("sheets")),
            "truncated": bool(raw.get("truncated")),
        }

        data_url = str(raw.get("data_url") or "")
        if data_url:
            if kind != "image":
                raise ValueError(f"附件 {filename} 不是图片，不能携带图片数据。")
            if len(data_url) > CHAT_IMAGE_MAX_DATA_URL_CHARS:
                raise ValueError(f"图片附件 {filename} 过大，已超过模型输入限制。")
            match = CHAT_IMAGE_DATA_URL_RE.match(data_url)
            if not match:
                raise ValueError(f"图片附件 {filename} 的数据格式无效。")
            compact_base64 = re.sub(r"\s+", "", match.group(2))
            try:
                decoded = base64.b64decode(compact_base64, validate=True)
            except Exception:
                raise ValueError(f"图片附件 {filename} 的 base64 内容无效。") from None
            if len(decoded) > CHAT_ATTACHMENT_MAX_SIZE:
                raise ValueError(f"图片附件 {filename} 超过 10MB 限制。")
            mime = f"image/{match.group(1).lower()}"
            if mime == "image/jpg":
                mime = "image/jpeg"
            item["content_type"] = mime
            item["data_url"] = f"data:{mime};base64,{compact_base64}"

        normalized.append(item)
    return normalized


def decode_text_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def zip_xml_texts(zf: zipfile.ZipFile, name: str) -> list[str]:
    try:
        root = ET.fromstring(zf.read(name))
    except Exception:
        return []
    return [
        node.text or ""
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] in {"t", "instrText"} and node.text
    ]


def extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        lines = zip_xml_texts(zf, "word/document.xml")
        return "\n".join(line.strip() for line in lines if line.strip())


def extract_xlsx_text(content: bytes) -> tuple[str, int, list[str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared_strings = zip_xml_texts(zf, "xl/sharedStrings.xml")
        workbook_names = zf.namelist()
        sheet_files = sorted(
            name
            for name in workbook_names
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        )
        output: list[str] = []
        row_count = 0
        sheet_labels: list[str] = []
        ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for index, sheet_name in enumerate(sheet_files[:5], start=1):
            sheet_labels.append(f"Sheet{index}")
            try:
                root = ET.fromstring(zf.read(sheet_name))
            except Exception:
                continue
            output.append(f"# Sheet{index}")
            for row in root.findall(".//x:sheetData/x:row", ns)[:80]:
                values: list[str] = []
                for cell in row.findall("x:c", ns)[:24]:
                    value_node = cell.find("x:v", ns)
                    inline_text = "".join(node.text or "" for node in cell.findall(".//x:t", ns))
                    if inline_text:
                        values.append(inline_text)
                    elif value_node is not None and value_node.text is not None:
                        if cell.get("t") == "s":
                            try:
                                values.append(shared_strings[int(value_node.text)])
                            except Exception:
                                values.append(value_node.text)
                        else:
                            values.append(value_node.text)
                if any(value.strip() for value in values):
                    row_count += 1
                    output.append(" | ".join(value.strip() for value in values))
        return "\n".join(output), row_count, sheet_labels


def extract_pdf_text(content: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ChatAttachmentError(
            415,
            "PDF 解析依赖 pypdf 未安装，请执行 pip install -r requirements.txt 后重试。",
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(content))
        pages: list[str] = []
        for page in reader.pages[:20]:
            pages.append(page.extract_text() or "")
    except Exception as exc:
        raise ChatAttachmentError(422, "PDF 文件无法解析或已加密。") from exc
    return "\n\n".join(page.strip() for page in pages if page.strip()), len(reader.pages)


def extract_xls_text(content: bytes) -> tuple[str, int, list[str]]:
    try:
        import xlrd
    except ImportError as exc:
        raise ChatAttachmentError(
            415,
            "旧版 Excel(.xls) 解析依赖 xlrd 未安装，请执行 pip install -r requirements.txt 后重试。",
        ) from exc

    try:
        workbook = xlrd.open_workbook(file_contents=content)
    except Exception as exc:
        raise ChatAttachmentError(422, "旧版 Excel(.xls) 文件无法解析。") from exc

    output: list[str] = []
    row_count = 0
    sheet_labels = workbook.sheet_names()[:5]
    for sheet_name in sheet_labels:
        sheet = workbook.sheet_by_name(sheet_name)
        output.append(f"# {sheet_name}")
        for row_index in range(min(sheet.nrows, 80)):
            values = [
                str(sheet.cell_value(row_index, col_index)).strip()
                for col_index in range(min(sheet.ncols, 24))
            ]
            if any(values):
                row_count += 1
                output.append(" | ".join(values))
    return "\n".join(output), row_count, sheet_labels


def image_attachment_text(safe_name: str, content_type: str, content: bytes) -> str:
    details = [
        f"图片文件：{safe_name}",
        f"MIME：{content_type or 'unknown'}",
        f"大小：{len(content)} bytes",
    ]
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            details.append(f"尺寸：{image.width}x{image.height}")
            details.append(f"格式：{image.format or 'unknown'}")
    except ImportError:
        details.append("尺寸：未读取（Pillow 未安装）")
    except Exception:
        details.append("尺寸：未读取（图片结构无法识别）")
    details.append("说明：如果当前模型支持视觉，图片会随本轮消息发送给模型；文本模型仅使用此图片摘要。")
    return "\n".join(details)


def preview_attachment_content(filename: str, content_type: str, content: bytes) -> dict:
    safe_name = os.path.basename(filename or "attachment")
    _, ext = os.path.splitext(safe_name)
    ext = ext.lower()
    guessed_content_type = mimetypes.guess_type(safe_name)[0]
    normalized_content_type = content_type or guessed_content_type or "application/octet-stream"
    if normalized_content_type == "application/octet-stream" and guessed_content_type:
        normalized_content_type = guessed_content_type
    rows = None
    sheets: list[str] = []
    pages = None
    kind = "document"
    data_url = None
    if ext in {".txt", ".md", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml", ".ini", ".conf", ".sql", ".xml"}:
        text = decode_text_bytes(content)
        if ext in {".csv", ".tsv"}:
            rows = max(0, len([line for line in text.splitlines() if line.strip()]))
    elif ext == ".docx":
        text = extract_docx_text(content)
    elif ext == ".doc":
        raise ChatAttachmentError(
            415,
            "旧版 Word(.doc) 是二进制格式，暂不在会话中直接解析；请另存为 .docx 后上传。",
        )
    elif ext == ".xlsx":
        text, rows, sheets = extract_xlsx_text(content)
    elif ext == ".xls":
        text, rows, sheets = extract_xls_text(content)
    elif ext == ".pdf":
        text, pages = extract_pdf_text(content)
    elif ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"} or normalized_content_type.startswith("image/"):
        kind = "image"
        text = image_attachment_text(safe_name, normalized_content_type, content)
        encoded = base64.b64encode(content).decode("ascii")
        candidate_data_url = f"data:{normalized_content_type};base64,{encoded}"
        if len(candidate_data_url) <= CHAT_IMAGE_MAX_DATA_URL_CHARS:
            data_url = candidate_data_url
        else:
            text += "\n注意：图片过大，已保留附件摘要，但不会直接作为视觉输入发送给模型。"
    else:
        raise ChatAttachmentError(415, f"暂不支持解析 {ext or 'unknown'} 文件。")

    text = re.sub(r"\r\n?", "\n", text).strip()
    max_chars = 20000
    truncated = len(text) > max_chars
    return {
        "filename": safe_name,
        "ext": ext,
        "size": len(content),
        "content_type": normalized_content_type,
        "text": text[:max_chars],
        "truncated": truncated,
        "rows": rows,
        "sheets": sheets,
        "pages": pages,
        "kind": kind,
        "data_url": data_url,
    }

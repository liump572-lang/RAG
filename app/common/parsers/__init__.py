from app.common.parsers.pdf_parser import parse_pdf
from app.common.parsers.docx_parser import parse_docx
from app.common.parsers.pptx_parser import parse_pptx
from app.common.parsers.txt_parser import parse_txt
from app.common.parsers.md_parser import parse_md


PARSER_MAP = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "pptx": parse_pptx,
    "txt": parse_txt,
    "md": parse_md,
}


def parse_document(file_path: str, file_type: str) -> str:
    parser = PARSER_MAP.get(file_type)
    if not parser:
        raise ValueError(f"Unsupported file type: {file_type}")
    return parser(file_path)

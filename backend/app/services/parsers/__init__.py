"""
多模态文件解析器
"""
from app.services.parsers.base import BaseParser, ParsedChunk, ParseResult
from app.services.parsers.pdf_parser import PDFParser
from app.services.parsers.docx_parser import WordParser
from app.services.parsers.video_parser import VideoParser
from app.services.parsers.factory import ParserFactory

__all__ = [
    "BaseParser",
    "ParsedChunk",
    "ParseResult",
    "PDFParser",
    "WordParser",
    "VideoParser",
    "ParserFactory",
]

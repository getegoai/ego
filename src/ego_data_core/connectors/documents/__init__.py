"""Document connector module."""

from ego_data_core.connectors.documents.parser import (
    DocumentParseResult,
    DocumentParser,
    DocumentParserError,
    MissingDocumentDependencyError,
    UnsupportedDocumentTypeError,
    split_text_into_chunks,
)

__all__ = [
    "DocumentParseResult",
    "DocumentParser",
    "DocumentParserError",
    "MissingDocumentDependencyError",
    "UnsupportedDocumentTypeError",
    "split_text_into_chunks",
]

"""
PDF Research Assistant Error Classes.

Custom exception classes for handling specific error conditions
in the PDF Research Assistant application.
"""

from .pdf_errors import (
    PDFProcessingError,
    EmbeddingError,
    RetrievalError,
    GenerationError,
)

__all__ = [
    "PDFProcessingError",
    "EmbeddingError", 
    "RetrievalError",
    "GenerationError",
] 
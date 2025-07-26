"""
Custom exception classes for PDF Research Assistant.

This module defines specific exception classes for different error conditions
that can occur during PDF processing, embedding generation, retrieval, and response generation.
"""


class PDFProcessingError(Exception):
    """
    Exception raised for errors in PDF processing.
    
    This includes errors in PDF upload, text extraction, or text chunking.
    """
    
    def __init__(self, message: str, file_path: str = None):
        """
        Initialize PDFProcessingError.
        
        Args:
            message (str): Error message.
            file_path (str, optional): Path to the problematic PDF file.
        """
        self.file_path = file_path
        super().__init__(f"PDF Processing Error: {message}")


class EmbeddingError(Exception):
    """
    Exception raised for errors in embedding generation or vector storage.
    
    This includes API errors, vector database connection issues, or indexing failures.
    """
    
    def __init__(self, message: str, document_id: str = None):
        """
        Initialize EmbeddingError.
        
        Args:
            message (str): Error message.
            document_id (str, optional): ID of the document being processed.
        """
        self.document_id = document_id
        super().__init__(f"Embedding Error: {message}")


class RetrievalError(Exception):
    """
    Exception raised for errors in document retrieval or similarity search.
    
    This includes search failures, context assembly issues, or database query problems.
    """
    
    def __init__(self, message: str, query: str = None):
        """
        Initialize RetrievalError.
        
        Args:
            message (str): Error message.
            query (str, optional): The search query that caused the error.
        """
        self.query = query
        super().__init__(f"Retrieval Error: {message}")


class GenerationError(Exception):
    """
    Exception raised for errors in response generation.
    
    This includes LLM API errors, prompt formatting issues, or response processing failures.
    """
    
    def __init__(self, message: str, query: str = None, context_length: int = None):
        """
        Initialize GenerationError.
        
        Args:
            message (str): Error message.
            query (str, optional): The user query that caused the error.
            context_length (int, optional): Length of context that may have caused the error.
        """
        self.query = query
        self.context_length = context_length
        super().__init__(f"Generation Error: {message}")


class ConfigurationError(Exception):
    """
    Exception raised for configuration-related errors.
    
    This includes missing API keys, invalid settings, or environment setup issues.
    """
    
    def __init__(self, message: str, config_key: str = None):
        """
        Initialize ConfigurationError.
        
        Args:
            message (str): Error message.
            config_key (str, optional): The configuration key that caused the error.
        """
        self.config_key = config_key
        super().__init__(f"Configuration Error: {message}") 
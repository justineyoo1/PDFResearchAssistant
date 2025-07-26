"""
Settings and configuration management for PDF Research Assistant.

This module handles loading and validation of environment variables,
API keys, and other configuration settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Configuration settings for the PDF Research Assistant."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # OpenAI Configuration
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        
        # Vector Database Configuration
        self.vector_db_type: str = os.getenv("VECTOR_DB_TYPE", "faiss")  # faiss or chromadb
        self.vector_db_path: str = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
        
        # PDF Processing Configuration
        self.pdf_upload_dir: str = os.getenv("PDF_UPLOAD_DIR", "./data/uploads")
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
        
        # Retrieval Configuration
        self.top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))
        self.similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
        
        # Streamlit Configuration
        self.app_title: str = os.getenv("APP_TITLE", "PDF Research Assistant")
        self.app_description: str = os.getenv(
            "APP_DESCRIPTION", 
            "Ask questions about your uploaded PDF documents using AI"
        )
        
        # Debug and Logging
        self.debug_mode: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Create necessary directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.vector_db_path,
            self.pdf_upload_dir,
            "./data/logs"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def validate_api_keys(self) -> bool:
        """
        Validate that required API keys are present.
        
        Returns:
            bool: True if all required API keys are present.
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return True
    
    def get_database_config(self) -> dict:
        """
        Get vector database configuration.
        
        Returns:
            dict: Database configuration parameters.
        """
        return {
            "type": self.vector_db_type,
            "path": self.vector_db_path,
            "similarity_threshold": self.similarity_threshold
        }
    
    def get_pdf_config(self) -> dict:
        """
        Get PDF processing configuration.
        
        Returns:
            dict: PDF processing configuration parameters.
        """
        return {
            "upload_dir": self.pdf_upload_dir,
            "max_file_size_mb": self.max_file_size_mb,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
    
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration.
        
        Returns:
            dict: LLM configuration parameters.
        """
        return {
            "api_key": self.openai_api_key,
            "model": self.openai_model,
            "embedding_model": self.embedding_model,
            "top_k_results": self.top_k_results
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.
    
    Returns:
        Settings: The global settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 
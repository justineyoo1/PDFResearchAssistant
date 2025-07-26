"""
Base classes for PDF Research Assistant components.

This module defines the abstract base classes that establish the interface
for all core components of the RAG system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class BaseIngester(ABC):
    """
    Abstract base class for PDF ingestion components.
    
    Handles PDF upload, parsing, and text extraction.
    """
    
    def __init__(self):
        """Initialize the ingester."""
        pass
    
    @abstractmethod
    def upload_pdf(self, file_path: str) -> bool:
        """
        Upload and validate a PDF file.
        
        Args:
            file_path (str): Path to the PDF file.
            
        Returns:
            bool: True if upload successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            file_path (str): Path to the PDF file.
            
        Returns:
            str: Extracted text content.
        """
        pass
    
    @abstractmethod
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks for processing.
        
        Args:
            text (str): Text to be chunked.
            chunk_size (int): Size of each chunk.
            overlap (int): Overlap between chunks.
            
        Returns:
            List[str]: List of text chunks.
        """
        pass


class BaseIndexer(ABC):
    """
    Abstract base class for document indexing components.
    
    Handles embedding generation and vector storage.
    """
    
    def __init__(self):
        """Initialize the indexer."""
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            texts (List[str]): List of text chunks.
            
        Returns:
            List[List[float]]: List of embedding vectors.
        """
        pass
    
    @abstractmethod
    def store_vectors(self, embeddings: List[List[float]], texts: List[str], metadata: Dict[str, Any]) -> str:
        """
        Store vectors in the vector database.
        
        Args:
            embeddings (List[List[float]]): Embedding vectors.
            texts (List[str]): Original text chunks.
            metadata (Dict[str, Any]): Document metadata.
            
        Returns:
            str: Document ID or status.
        """
        pass
    
    @abstractmethod
    def create_index(self, document_id: str) -> bool:
        """
        Create searchable index for a document.
        
        Args:
            document_id (str): Unique document identifier.
            
        Returns:
            bool: True if index created successfully.
        """
        pass


class BaseRetriever(ABC):
    """
    Abstract base class for document retrieval components.
    
    Handles similarity search and context retrieval.
    """
    
    def __init__(self):
        """Initialize the retriever."""
        pass
    
    @abstractmethod
    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform similarity search for a query.
        
        Args:
            query (str): User query.
            top_k (int): Number of top results to return.
            
        Returns:
            List[Dict[str, Any]]: List of relevant document chunks with metadata.
        """
        pass
    
    @abstractmethod
    def get_context(self, query: str, document_id: Optional[str] = None) -> str:
        """
        Get relevant context for a query.
        
        Args:
            query (str): User query.
            document_id (Optional[str]): Specific document to search in.
            
        Returns:
            str: Concatenated relevant context.
        """
        pass


class BaseGenerator(ABC):
    """
    Abstract base class for response generation components.
    
    Handles LLM interaction and response generation using RAG.
    """
    
    def __init__(self):
        """Initialize the generator."""
        pass
    
    @abstractmethod
    def generate_response(self, query: str, context: str) -> str:
        """
        Generate a response using the LLM with provided context.
        
        Args:
            query (str): User query.
            context (str): Retrieved context from documents.
            
        Returns:
            str: Generated response.
        """
        pass
    
    @abstractmethod
    def format_prompt(self, query: str, context: str) -> str:
        """
        Format the prompt for the LLM.
        
        Args:
            query (str): User query.
            context (str): Retrieved context.
            
        Returns:
            str: Formatted prompt.
        """
        pass


class BaseManager(ABC):
    """
    Abstract base class for managing the entire RAG pipeline.
    
    Orchestrates ingestion, indexing, retrieval, and generation.
    """
    
    def __init__(self):
        """Initialize the manager."""
        pass
    
    @abstractmethod
    def process_pdf(self, file_path: str) -> str:
        """
        Process a PDF through the entire pipeline.
        
        Args:
            file_path (str): Path to the PDF file.
            
        Returns:
            str: Document ID or processing status.
        """
        pass
    
    @abstractmethod
    def ask_question(self, query: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ask a question and get an answer using RAG.
        
        Args:
            query (str): User question.
            document_id (Optional[str]): Specific document to query.
            
        Returns:
            Dict[str, Any]: Response with answer, sources, and metadata.
        """
        pass
    
    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all processed documents.
        
        Returns:
            List[Dict[str, Any]]: List of document metadata.
        """
        pass 
"""
Data models for document processing and RAG system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime
from backend.data_objects import Country


class DocumentType(str, Enum):
    """Types of documents that can be processed"""
    PDF = "pdf"
    DOCX = "docx" 
    TXT = "txt"
    WEB_LINK = "web_link"
    
class DocumentSource(BaseModel):
    """Represents a processed document"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Document name or URL")
    type: DocumentType = Field(description="Type of document")
    content: str = Field(description="Extracted text content")
    upload_date: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata like page count, author, etc.")

class DocumentChunk(BaseModel):
    """Represents a chunk of a document for vector storage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = Field(description="Reference to parent document")
    content: str = Field(description="Text chunk content")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    chunk_index: int = Field(description="Order of this chunk in the document")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Citation(BaseModel):
    """Citation from a document source"""
    document_id: str = Field(description="Source document ID")
    document_name: str = Field(description="Source document name")
    page_number: Optional[int] = Field(default=None)
    quote: str = Field(description="Exact text quote")
    relevance_score: float = Field(description="Relevance score from vector search")

class EnhancedLegalAnalysisRequest(BaseModel):
    """Request for legal analysis with document support"""
    survey_id: str
    country: str
    model: str = "gpt-5"
    document_ids: List[str] = Field(default_factory=list, description="IDs of uploaded documents to include")
    web_links: List[str] = Field(default_factory=list, description="Web links to analyze")

class CustomLegalQueryRequest(BaseModel):
    """Request for custom legal queries with document support"""
    question: str = Field(description="Custom legal question")
    country: str
    model: str = "gpt-5"
    document_ids: List[str] = Field(default_factory=list, description="IDs of uploaded documents to include")
    web_links: List[str] = Field(default_factory=list, description="Web links to analyze")
    
class EnhancedLegalAnalysisResponse(BaseModel):
    """Enhanced legal analysis response with citations"""
    survey_id: str
    country: Country
    question: str
    answer: str
    legal_basis: str
    additional_notes: Optional[str] = None
    confidence_level: str
    is_cached: Optional[bool] = False
    
    # New fields for document analysis
    citations: List[Citation] = Field(default_factory=list, description="Source citations")
    documents_analyzed: int = Field(default=0, description="Number of documents analyzed")
    web_sources_count: int = Field(default=0, description="Number of web sources analyzed")

class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    document_id: str
    name: str
    type: DocumentType
    content_length: int
    upload_date: datetime
    
class WebLinkResponse(BaseModel):
    """Response for web link processing"""
    document_id: str
    name: str
    type: DocumentType
    content_length: int
    domain: str

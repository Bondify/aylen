"""
Document processing service for RAG system
Handles file upload, text extraction, chunking, and vector search
"""

import os
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import tempfile
import fitz  # PyMuPDF for PDF processing
from docx import Document as DocxDocument
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from backend.tools.document_models import DocumentSource, DocumentChunk, DocumentType, Citation

class DocumentProcessor:
    """Handles document processing and vector search for RAG system"""
    
    def __init__(self, storage_path: str = "documents/", chroma_path: str = "./chroma_db"):
        self.storage_path = storage_path
        self.chroma_path = chroma_path
        
        # Initialize sentence transformer for embeddings
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Failed to load sentence transformer: {e}")
            self.embedder = None
        
        # Initialize ChromaDB for vector storage
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="legal_documents",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Warning: Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # In-memory storage for documents (as fallback)
        self.documents: Dict[str, DocumentSource] = {}
        self.chunks: Dict[str, List[DocumentChunk]] = {}
    
    async def process_uploaded_file(self, file_content: bytes, filename: str) -> DocumentSource:
        """Process an uploaded file and extract text"""
        file_ext = filename.lower().split('.')[-1]
        
        try:
            if file_ext == 'pdf':
                content = self._extract_from_pdf(file_content)
                doc_type = DocumentType.PDF
            elif file_ext == 'docx':
                content = self._extract_from_docx(file_content)
                doc_type = DocumentType.DOCX
            elif file_ext == 'txt':
                content = file_content.decode('utf-8')
                doc_type = DocumentType.TXT
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Create document source
            doc_source = DocumentSource(
                name=filename,
                type=doc_type,
                content=content,
                metadata={"file_size": len(file_content)}
            )
            
            # Store document in memory
            self.documents[doc_source.id] = doc_source
            
            # Create chunks and store in vector database
            await self._chunk_and_store_document(doc_source)
            
            return doc_source
            
        except Exception as e:
            raise ValueError(f"Failed to process file {filename}: {str(e)}")
    
    async def process_web_link(self, url: str) -> DocumentSource:
        """Process a web link and extract text"""
        try:
            # Additional URL encoding safety check for backend
            original_url = url
            try:
                # Try to parse and properly encode the URL
                from urllib.parse import urlparse, urlunparse, quote
                parsed = urlparse(url)
                # Encode the path component which often contains special characters
                encoded_path = quote(parsed.path, safe='/')
                # Reconstruct the URL with encoded components
                url = urlunparse((
                    parsed.scheme, parsed.netloc, encoded_path,
                    parsed.params, parsed.query, parsed.fragment
                ))
                if url != original_url:
                    print(f"🔧 URL encoded: {original_url} → {url}")
            except Exception as e:
                print(f"⚠️ URL encoding failed, using original: {e}")
                url = original_url
            
            # Use a timeout to avoid hanging
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # First, make a HEAD request to check content type
                try:
                    async with session.head(url, headers=headers) as head_response:
                        content_type = head_response.headers.get('content-type', '').lower()
                        print(f"🔍 Content-Type detected: {content_type}")
                except:
                    # If HEAD fails, we'll detect based on URL extension
                    content_type = ""
                
                # Detect file type from URL extension or content-type
                url_lower = url.lower()
                is_pdf = content_type.startswith('application/pdf') or url_lower.endswith('.pdf')
                is_docx = content_type.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document') or url_lower.endswith('.docx')
                is_doc = content_type.startswith('application/msword') or url_lower.endswith('.doc')
                
                if is_pdf or is_docx or is_doc:
                    # Download as binary for document processing
                    print(f"📄 Processing as document file: {'PDF' if is_pdf else 'DOCX' if is_docx else 'DOC'}")
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise ValueError(f"HTTP {response.status}: Failed to fetch {url}")
                        file_content = await response.read()
                    
                    # Process based on file type
                    if is_pdf:
                        content = self._extract_from_pdf(file_content)
                        doc_type = DocumentType.PDF
                    elif is_docx:
                        content = self._extract_from_docx(file_content)
                        doc_type = DocumentType.DOCX
                    else:  # DOC files would need additional handling
                        raise ValueError("DOC files are not supported. Please convert to PDF or DOCX.")
                        
                    # Set document name based on URL
                    document_name = url.split('/')[-1] if '/' in url else url
                    
                else:
                    # Process as HTML/web page
                    print(f"🌐 Processing as web page")
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise ValueError(f"HTTP {response.status}: Failed to fetch {url}")
                        html_content = await response.text()
                    
                    # Extract text using BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    
                    # Get text and clean it up
                    content = soup.get_text()
                    lines = (line.strip() for line in content.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    content = ' '.join(chunk for chunk in chunks if chunk)
                    
                    doc_type = DocumentType.WEB_LINK
                    document_name = url
            
            # Basic validation
            if len(content) < 100:
                raise ValueError("Extracted content too short - might not be a valid document")
            
            doc_source = DocumentSource(
                name=document_name,
                type=doc_type,
                content=content,
                metadata={
                    "domain": urlparse(url).netloc,
                    "url": url,
                    "content_length": len(content),
                    "original_content_type": content_type
                }
            )
            
            # Store document in memory
            self.documents[doc_source.id] = doc_source
            
            # Create chunks and store in vector database
            await self._chunk_and_store_document(doc_source)
            
            return doc_source
            
        except Exception as e:
            raise ValueError(f"Failed to process web link {url}: {str(e)}")
    
    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text = ""
            for page in doc:
                page_text = page.get_text()
                if page_text.strip():  # Only add non-empty pages
                    text += f"\n--- Page {page.number + 1} ---\n{page_text}"
            doc.close()
            
            if not text.strip():
                raise ValueError("No text content found in PDF")
                
            return text
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            # Save temporarily to process with python-docx
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            try:
                doc = DocxDocument(temp_path)
                text = ""
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text += paragraph.text + "\n"
                
                if not text.strip():
                    raise ValueError("No text content found in DOCX")
                    
                return text
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")
    
    async def _chunk_and_store_document(self, doc_source: DocumentSource, chunk_size: int = 1000, overlap: int = 200):
        """Chunk document and store in vector database"""
        content = doc_source.content
        chunks = []
        
        # Improved chunking with overlap
        if len(content) <= chunk_size:
            # Document is small, use as single chunk
            chunk = DocumentChunk(
                document_id=doc_source.id,
                content=content,
                chunk_index=0,
                metadata={"start_char": 0, "end_char": len(content)}
            )
            chunks.append(chunk)
        else:
            # Split into overlapping chunks
            start = 0
            chunk_index = 0
            while start < len(content):
                end = min(start + chunk_size, len(content))
                chunk_content = content[start:end]
                
                # Try to break at sentence boundaries
                if end < len(content) and '.' in chunk_content:
                    last_period = chunk_content.rfind('.')
                    if last_period > len(chunk_content) * 0.5:  # Only if period is in latter half
                        end = start + last_period + 1
                        chunk_content = content[start:end]
                
                chunk = DocumentChunk(
                    document_id=doc_source.id,
                    content=chunk_content.strip(),
                    chunk_index=chunk_index,
                    metadata={"start_char": start, "end_char": end}
                )
                chunks.append(chunk)
                
                # Move start position with overlap
                start = end - overlap
                if start >= len(content):
                    break
                chunk_index += 1
        
        # Store chunks in memory
        self.chunks[doc_source.id] = chunks
        
        # Generate embeddings and store in ChromaDB if available
        if self.embedder and self.collection and chunks:
            try:
                chunk_contents = [chunk.content for chunk in chunks]
                embeddings = self.embedder.encode(chunk_contents).tolist()
                
                self.collection.add(
                    embeddings=embeddings,
                    documents=chunk_contents,
                    metadatas=[{
                        "document_id": chunk.document_id,
                        "document_name": doc_source.name,
                        "chunk_index": chunk.chunk_index,
                        "document_type": doc_source.type.value,
                        "start_char": chunk.metadata["start_char"],
                        "end_char": chunk.metadata["end_char"]
                    } for chunk in chunks],
                    ids=[chunk.id for chunk in chunks]
                )
            except Exception as e:
                print(f"Warning: Failed to store embeddings: {e}")
    
    async def search_documents(self, query: str, document_ids: List[str] = None, top_k: int = 5) -> List[Citation]:
        """Search for relevant document chunks"""
        citations = []
        
        # Try vector search first if available
        if self.embedder and self.collection:
            try:
                query_embedding = self.embedder.encode([query]).tolist()
                
                # Build where clause for document filtering
                where_clause = None
                if document_ids:
                    where_clause = {"document_id": {"$in": document_ids}}
                
                results = self.collection.query(
                    query_embeddings=query_embedding,
                    n_results=top_k,
                    where=where_clause,
                    include=["documents", "metadatas", "distances"]
                )
                
                if results['documents'] and results['documents'][0]:
                    for doc, metadata, distance in zip(
                        results['documents'][0], 
                        results['metadatas'][0], 
                        results['distances'][0]
                    ):
                        citation = Citation(
                            document_id=metadata['document_id'],
                            document_name=metadata['document_name'],
                            quote=doc[:300] + "..." if len(doc) > 300 else doc,
                            relevance_score=max(0, 1 - distance),  # Convert distance to similarity
                            page_number=metadata.get('page_number')
                        )
                        citations.append(citation)
                
                return citations
                
            except Exception as e:
                print(f"Warning: Vector search failed, falling back to text search: {e}")
        
        # Fallback to simple text search
        citations = self._fallback_text_search(query, document_ids, top_k)
        return citations
    
    def _fallback_text_search(self, query: str, document_ids: List[str] = None, top_k: int = 5) -> List[Citation]:
        """Fallback text search when vector search is not available"""
        citations = []
        query_lower = query.lower()
        
        # Search through stored chunks
        for doc_id, chunks in self.chunks.items():
            if document_ids and doc_id not in document_ids:
                continue
                
            doc_source = self.documents.get(doc_id)
            if not doc_source:
                continue
            
            for chunk in chunks:
                chunk_lower = chunk.content.lower()
                # Simple relevance scoring based on query term frequency
                score = sum(1 for term in query_lower.split() if term in chunk_lower)
                
                if score > 0:
                    citation = Citation(
                        document_id=doc_id,
                        document_name=doc_source.name,
                        quote=chunk.content[:300] + "..." if len(chunk.content) > 300 else chunk.content,
                        relevance_score=min(1.0, score / len(query.split())),
                        page_number=chunk.page_number
                    )
                    citations.append(citation)
        
        # Sort by relevance score and return top_k
        citations.sort(key=lambda x: x.relevance_score, reverse=True)
        return citations[:top_k]
    
    def get_document_info(self, document_id: str) -> Optional[DocumentSource]:
        """Get document information by ID"""
        return self.documents.get(document_id)
    
    def list_documents(self) -> List[DocumentSource]:
        """List all stored documents"""
        return list(self.documents.values())

# Global instance
document_processor = DocumentProcessor()

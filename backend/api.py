"""
FastAPI wrapper for the Legal AI Agent
Provides REST API endpoints for the React frontend
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path to import legal_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from legal_agent import (
    load_survey, 
    Country, 
    LegalAnalysisResponse,
    analyze_legal_query,
    analyze_legal_query_with_documents,
    AIModel,
    chat_about_legal_response
)
from backend.data_objects import MODEL_INFO
from backend.document_models import (
    EnhancedLegalAnalysisRequest, 
    EnhancedLegalAnalysisResponse, 
    CustomLegalQueryRequest,
    DocumentUploadResponse, 
    WebLinkResponse
)
from backend.document_service import document_processor

from backend.cache_service import cache

app = FastAPI(title="Legal AI Agent API", description="REST API for Legal AI Analysis")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class AnalysisRequest(BaseModel):
    survey_id: str
    countries: List[str]
    model: str = AIModel.GPT_5

class EntireSurveyRequest(BaseModel):
    country: str
    model: str = AIModel.GPT_5

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    cost: str

class SurveyInfo(BaseModel):
    id: str
    question: str
    criteria: str

class CountryInfo(BaseModel):
    code: str
    name: str

class ThreadMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ThreadChatRequest(BaseModel):
    message: str
    response_id: str  # Format: survey_id|country|model
    conversation_history: List[ThreadMessage] = []
    model: str = AIModel.GPT_4O_MINI

class ThreadChatResponse(BaseModel):
    message: str
    response_id: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Legal AI Agent API is running"}

@app.get("/surveys", response_model=List[SurveyInfo])
async def get_surveys():
    """Get all available survey questions"""
    surveys = []
    raw_surveys = load_survey()
    for survey_id, survey in raw_surveys.items():
        surveys.append(SurveyInfo(
            id=survey.id,
            question=survey.question,
            criteria=survey.criteria
        ))
    return surveys

@app.get("/countries", response_model=List[CountryInfo])
async def get_countries():
    """Get all available countries"""
    countries = []
    for country in Country:
        countries.append(CountryInfo(
            code=country.value,
            name=country.value
        ))
    return countries

@app.get("/models", response_model=List[ModelInfo])
async def get_models():
    """Get all available AI models"""
    models = []
    for model_id, info in MODEL_INFO.items():
        models.append(ModelInfo(
            id=model_id.value,
            name=info["name"],
            provider=info["provider"],
            description=info["description"],
            cost=info["cost"]
        ))
    return models

@app.post("/analyze", response_model=List[LegalAnalysisResponse])
async def analyze_survey(request: AnalysisRequest):
    """Analyze a survey question across multiple countries with persistent caching"""
    try:
        # Load surveys and validate survey ID
        raw_surveys = load_survey()
        if request.survey_id not in raw_surveys:
            raise HTTPException(
                status_code=404, 
                detail=f"Survey '{request.survey_id}' not found"
            )
        
        # Validate model
        try:
            model_choice = AIModel(request.model)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model: {request.model}"
            )
        
        # Validate and convert countries
        countries = []
        for country_name in request.countries:
            try:
                country = Country(country_name)
                countries.append(country)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid country: {country_name}"
                )
        
        # Get survey details
        survey = raw_surveys[request.survey_id]
        
        # Process with persistent caching
        results = []
        cache_hits = 0
        api_calls = 0
        
        for country in countries:
            # Try cache first
            cached_response = cache.get_cached_response(
                survey_id=request.survey_id,
                question=survey.question,
                criteria=survey.criteria,
                country=country.value,
                model=request.model
            )
            
            if cached_response:
                # Add cache indicator to response
                cached_response.is_cached = True  # 👈 NEW: Mark as cached
                results.append(cached_response)
                cache_hits += 1
            else:
                # Cache miss - make API call
                result = await analyze_legal_query(
                    survey.question,
                    country,
                    survey.criteria,
                    model_choice
                )
                result.survey_id = request.survey_id
                result.question = survey.question
                result.is_cached = False  # 👈 NEW: Mark as fresh
                
                # Store in persistent cache
                cache.store_response(
                    survey_id=request.survey_id,
                    question=survey.question,
                    criteria=survey.criteria,
                    country=country.value,
                    model=request.model,
                    response=result
                )
                
                results.append(result)
                api_calls += 1
        
        print(f"📊 Cache Performance: {cache_hits}/{len(countries)} hits ({cache_hits/len(countries)*100:.1f}%), {api_calls} API calls")
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-entire-survey", response_model=List[LegalAnalysisResponse])
async def analyze_entire_survey(request: EntireSurveyRequest):
    """Analyze all survey questions for a single country with persistent caching"""
    try:
        # Validate country
        try:
            country = Country(request.country)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid country: {request.country}"
            )
        
        # Validate model
        try:
            model_choice = AIModel(request.model)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model: {request.model}"
            )
        
        # Load all surveys
        raw_surveys = load_survey()
        
        # Analyze each survey question with caching
        results = []
        cache_hits = 0
        api_calls = 0
        
        for survey_id, survey in raw_surveys.items():
            try:
                # Check cache first
                cached_response = cache.get_cached_response(
                    survey_id=survey_id,
                    question=survey.question,
                    criteria=survey.criteria,
                    country=country.value,
                    model=request.model
                )
                
                if cached_response:
                    cached_response.is_cached = True  # 👈 NEW: Mark as cached
                    results.append(cached_response)
                    cache_hits += 1
                else:
                    # Cache miss - make API call
                    result = await analyze_legal_query(
                        survey.question,
                        country,
                        survey.criteria,
                        model_choice
                    )
                    result.survey_id = survey_id
                    result.question = survey.question
                    result.is_cached = False  # 👈 NEW: Mark as fresh
                    
                    # Store in cache
                    cache.store_response(
                        survey_id=survey_id,
                        question=survey.question,
                        criteria=survey.criteria,
                        country=country.value,
                        model=request.model,
                        response=result
                    )
                    
                    results.append(result)
                    api_calls += 1
                    
            except Exception as e:
                print(f"Error analyzing survey {survey_id} for {country.value}: {e}")
                continue
        
        print(f"📊 Cache Performance: {cache_hits}/{len(raw_surveys)} hits ({cache_hits/len(raw_surveys)*100:.1f}%), {api_calls} API calls")
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add cache management endpoints
@app.get("/cache/stats")
async def get_cache_stats():
    """Get detailed cache statistics"""
    try:
        stats = cache.get_cache_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.delete("/cache/survey/{survey_id}")
async def invalidate_survey_cache(survey_id: str):
    """Invalidate all cached responses for a specific survey"""
    try:
        count = cache.invalidate_survey(survey_id)
        return {"message": f"Invalidated {count} cached responses for survey: {survey_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@app.get("/cache/surveys/{country}/{model}")
async def get_cached_surveys(country: str, model: str):
    """Get list of surveys with cached responses for a country-model combination"""
    try:
        surveys = cache.get_cached_surveys_for_country(country, model)
        return {"country": country, "model": model, "cached_surveys": surveys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cached surveys: {str(e)}")


# RAG ENDPOINTS - Document Upload & Enhanced Analysis

@app.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document for analysis"""
    try:
        # Read file content
        content = await file.read()
        
        # Validate file size (10MB max)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
        # Process document
        doc_source = await document_processor.process_uploaded_file(content, file.filename)
        
        return DocumentUploadResponse(
            document_id=doc_source.id,
            name=doc_source.name,
            type=doc_source.type,
            content_length=len(doc_source.content),
            upload_date=doc_source.upload_date
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@app.post("/analyze-web-link", response_model=WebLinkResponse)
async def analyze_web_link(url: str = Form(...)):
    """Process a web link for analysis"""
    try:
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
            
        # Process web link
        doc_source = await document_processor.process_web_link(url)
        
        return WebLinkResponse(
            document_id=doc_source.id,
            name=doc_source.name,
            type=doc_source.type,
            content_length=len(doc_source.content),
            domain=doc_source.metadata.get("domain", "")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process web link: {str(e)}")

@app.post("/analyze-enhanced", response_model=EnhancedLegalAnalysisResponse)
async def analyze_with_documents(request: EnhancedLegalAnalysisRequest):
    """Enhanced legal analysis with document support (RAG)"""
    try:
        # Load surveys and validate
        raw_surveys = load_survey()
        if request.survey_id not in raw_surveys:
            raise HTTPException(status_code=404, detail=f"Survey '{request.survey_id}' not found")
        
        survey = raw_surveys[request.survey_id]
        
        # Validate country and model
        try:
            country = Country(request.country)
            model_choice = AIModel(request.model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Perform enhanced analysis with documents
        result = await analyze_legal_query_with_documents(
            question=survey.question,
            country=country,
            criteria=survey.criteria,
            model_choice=model_choice,
            survey_id=request.survey_id,
            document_ids=request.document_ids,
            web_links=request.web_links
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-custom", response_model=EnhancedLegalAnalysisResponse)
async def analyze_custom_query(request: CustomLegalQueryRequest):
    """Analyze custom legal question with document support (RAG)"""
    try:
        # Validate country and model
        try:
            country = Country(request.country)
            model_choice = AIModel(request.model)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Perform enhanced analysis with documents
        result = await analyze_legal_query_with_documents(
            question=request.question,
            country=country,
            criteria="Provide comprehensive legal analysis based on available information and uploaded documents.",
            model_choice=model_choice,
            survey_id="custom_query",
            document_ids=request.document_ids,
            web_links=request.web_links
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search-documents")
async def search_documents(query: str, document_ids: str = None, top_k: int = 5):
    """Search through uploaded documents"""
    try:
        # Parse document IDs
        doc_ids = None
        if document_ids:
            doc_ids = [doc_id.strip() for doc_id in document_ids.split(',') if doc_id.strip()]
        
        # Search documents
        citations = await document_processor.search_documents(query, doc_ids, top_k)
        
        return {
            "query": query,
            "document_ids": doc_ids,
            "citations": [citation.dict() for citation in citations]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents = document_processor.list_documents()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "name": doc.name,
                    "type": doc.type.value,
                    "upload_date": doc.upload_date.isoformat(),
                    "content_length": len(doc.content),
                    "metadata": doc.metadata
                }
                for doc in documents
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{document_id}")
async def get_document_info(document_id: str):
    """Get information about a specific document"""
    try:
        doc = document_processor.get_document_info(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": doc.id,
            "name": doc.name,
            "type": doc.type.value,
            "upload_date": doc.upload_date.isoformat(),
            "content_length": len(doc.content),
            "metadata": doc.metadata,
            "content_preview": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/thread/chat", response_model=ThreadChatResponse)
async def thread_chat(request: ThreadChatRequest):
    """Chat about a specific legal analysis response"""
    try:
        # Parse the response_id to get the original response details
        # Format: survey_id|country|model
        try:
            survey_id, country_name, model_used = request.response_id.split("|")
            country = Country(country_name)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid response_id format. Expected: survey_id|country|model"
            )
        
        # Try to get the original response from cache
        raw_surveys = load_survey()
        if survey_id not in raw_surveys:
            raise HTTPException(
                status_code=404,
                detail=f"Survey '{survey_id}' not found"
            )
        
        survey = raw_surveys[survey_id]
        
        # Get the original response from cache
        original_response = cache.get_cached_response(
            survey_id=survey_id,
            question=survey.question,
            criteria=survey.criteria,
            country=country_name,
            model=model_used
        )
        
        if not original_response:
            # If not in cache, we need to create a basic response object
            # This shouldn't happen often, but we'll handle it gracefully
            original_response = LegalAnalysisResponse(
                survey_id=survey_id,
                country=country,
                question=survey.question,
                answer="Original analysis not found in cache",
                legal_basis="Please refer to the original analysis",
                confidence_level="Medium"
            )
        
        # Validate model choice
        try:
            model_choice = AIModel(request.model)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model: {request.model}"
            )
        
        # Convert conversation history
        history = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.conversation_history
        ]
        
        # Get chat response
        response_message = await chat_about_legal_response(
            message=request.message,
            original_response=original_response,
            conversation_history=history,
            model_choice=model_choice
        )
        
        return ThreadChatResponse(
            message=response_message,
            response_id=request.response_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
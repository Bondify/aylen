from typing import Optional
from pydantic import Field, BaseModel
from enum import Enum


class AIModel(str, Enum):
    """Available AI models for legal analysis"""
    GPT_5 = "gpt-5"
    GPT_4O = "gpt-4o" 
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"


# Model information for UI display
MODEL_INFO = {
    AIModel.GPT_5: {
        "name": "GPT-5",
        "provider": "OpenAI",
        "description": "Latest OpenAI model",
        "cost": "Very High"
    },
    AIModel.GPT_4O_MINI: {
        "name": "GPT-4o Mini", 
        "provider": "OpenAI",
        "description": "Fast and cost-effective",
        "cost": "Very Low"
    },
    AIModel.GPT_4O: {
        "name": "GPT-4o",
        "provider": "OpenAI", 
        "description": "Previous generation model",
        "cost": "Medium"
    },
    AIModel.CLAUDE_3_5_SONNET: {
        "name": "Claude 3.5 Sonnet",
        "provider": "AWS Bedrock",
        "description": "Excellent for complex reasoning",
        "cost": "High"
    }
}


class Country(str, Enum):
    """Supported countries for legal analysis"""
    FRANCE = "France"
    SPAIN = "Spain"
    SAUDI_ARABIA = "Saudi Arabia"
    UNITED_STATES = "United States"
    GERMANY = "Germany"
    UNITED_KINGDOM = "United Kingdom"
    CANADA = "Canada"
    ANTIGUA_AND_BARBUDA = "Antigua and Barbuda"
    EL_SALVADOR = "El Salvador"
    BOLIVIA = "Bolivia"
    GUYANA = "Guyana"
    ECUADOR = "Ecuador"


COUNTRY_LANGUAGES = {
    Country.FRANCE: ("French", "fr"),
    Country.SPAIN: ("Spanish", "es"),
    Country.SAUDI_ARABIA: ("Arabic", "ar"),
    Country.UNITED_STATES: ("English", "en"),
    Country.GERMANY: ("German", "de"),
    Country.UNITED_KINGDOM: ("English", "en"),
    Country.CANADA: ("English", "en"),
    Country.ANTIGUA_AND_BARBUDA: ("English", "en"),
    Country.EL_SALVADOR: ("Spanish", "es"),
    Country.BOLIVIA: ("Spanish", "es"),
    Country.GUYANA: ("English", "en"),
    Country.ECUADOR: ("Spanish", "es"),
}


class LegalQuery(BaseModel):
    """Survey question model"""
    id: str = Field(description="Unique identifier for the survey")
    question: str = Field(description="The legal question to analyze")
    criteria: str = Field(description="Detailed criteria for analysis")


class LegalAnalysisResponse(BaseModel):
    """Structured response for legal queries with consistent criteria"""
    survey_id: str = Field(description="The survey ID being analyzed")
    country: Country = Field(description="The country being analyzed")
    question: str = Field(description="The survey question being analyzed")
    answer: str = Field(description="Direct answer to the legal question")
    legal_basis: str = Field(description="The legal framework or laws that support this answer")
    additional_notes: Optional[str] = Field(
        default=None,
        description="Important caveats, recent changes, or regional variations"
    )
    confidence_level: str = Field(
        description="Confidence level: High, Medium, or Low based on clarity of legal framework"
    )
    is_cached: Optional[bool] = Field(  # 👈 NEW: Cache indicator
        default=False,
        description="Whether this response came from cache"
    )

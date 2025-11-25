from ast import List
from typing import Optional, Union
from pydantic import Field, BaseModel
from enum import Enum
import pandas as pd
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.models.anthropic import AnthropicModel


class AIModel(OpenAIResponsesModel, GoogleModel, AnthropicModel):
    """Available AI models for legal analysis"""
    GPT_4O_MINI = OpenAIResponsesModel("gpt-4o-mini")
    GPT_5 = OpenAIResponsesModel("gpt-5")
    GPT_4_1 = OpenAIResponsesModel("gpt-4.1")
    GPT_5_MINI = OpenAIResponsesModel("gpt-5-mini")
    CLAUDE_3_5_SONNET = AnthropicModel("claude-3.5-sonnet-latest")
    CLAUDE_4_SONNET = AnthropicModel("claude-sonnet-4-0")
    CLAUDE_4_5_SONNET = AnthropicModel("claude-sonnet-4-5") 
    GEMINI_2_5_FLASH = GoogleModel("gemini-2.5-flash")
    GEMINI_2_5_PRO = GoogleModel("gemini-2.5-pro")
    GEMINI_2_5_FLASH_LITE = GoogleModel("gemini-2.5-flash-lite")

# # Model information for UI display
# MODEL_INFO = {
#     AIModel.GPT_5: {
#         "name": "GPT-5",
#         "provider": "OpenAI",
#         "description": "Latest OpenAI model",
#         "cost": "Very High"
#     },
#     AIModel.GPT_5_MINI: {
#         "name": "GPT-5 Mini", 
#         "provider": "OpenAI",
#         "description": "Fast and cost-effective",
#         "cost": "Very Low"
#     },
#     AIModel.GPT_4_1: {
#         "name": "GPT-4.1",
#         "provider": "OpenAI", 
#         "description": "Previous generation model",
#         "cost": "Medium"
#     },
#     AIModel.CLAUDE_3_5_SONNET: {
#         "name": "Claude 3.5 Sonnet",
#         "provider": "Anthropic",
#         "description": "Excellent for complex reasoning",
#         "cost": "Medium"
#     },
#     AIModel.CLAUDE_4_SONNET: {
#         "name": "Claude 4 Sonnet",
#         "provider": "Anthropic",
#         "description": "Previous generation Claude model with superior reasoning and accuracy",
#         "cost": "Very High"
#     },
#     AIModel.CLAUDE_4_5_SONNET: {
#         "name": "Claude 4.5 Sonnet",
#         "provider": "Anthropic",
#         "description": "Latest Claude model with superior reasoning and accuracy",
#         "cost": "Very High"
#     },
#     AIModel.GEMINI_2_5_FLASH: {
#         "name": "Gemini 2.5 Flash",
#         "provider": "Google",
#         "description": "Best price to performance ratio",
#         "cost": "Low"
#     },
#     AIModel.GEMINI_2_5_PRO: {
#         "name": "Gemini 2.5 Pro",
#         "provider": "Google",
#         "description": "Best performance and accuracy",
#         "cost": "High"
#     },
#     AIModel.GEMINI_2_5_FLASH_LITE: {
#         "name": "Gemini 2.5 Flash Lite",
#         "provider": "Google",
#         "description": "Cheapest and fastest Gemini model",
#         "cost": "Low"
#     }
# }

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
    NIGERIA = "Nigeria"
    EGYPT = "Egypt, Arab Rep."


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
    Country.NIGERIA: ("English", "en"),
    Country.EGYPT: ("Arabic", "ar"),
}


class Topic(str, Enum):
    PARENTHOOD = "Parenthood"
    ENTREPRENEURSHIP = "Entrepreneurship"
    ASSETS = "Assets"
    PENSION = "Pension"
    WORKPLACE = "Workplace"
    PAY = "Pay"
    MOBILITY = "Mobility"
    MARRIAGE = "Marriage"


class LegalQuery(BaseModel):
    """Survey question model"""
    id: str = Field(description="Unique identifier for the survey")
    question: str = Field(description="The legal question to analyze")
    criteria: str = Field(description="Detailed criteria for analysis")


class BinaryAnswer(str, Enum):
    """Binary answers for yes/no questions"""
    YES = "Yes"
    NO = "No"
    DONT_KNOW = "Don't know"
    NOT_APPLICABLE = "Not applicable"


class MarriageRegime(str, Enum):
    """Common marriage property regimes"""
    SEPARATION_OF_PROPERTY = "Separation of property"
    PARTIAL_COMMUNITY = "Partial community of property"


class LegalAnalysisResponse(BaseModel):
    """Structured response for legal queries with consistent criteria"""
    # survey_id: str = Field(description="The survey ID being analyzed")
    country: Country = Field(description="The country being analyzed")
    topic: Topic = Field(description="The topic being analyzed")
    question: str = Field(description="The survey question being analyzed")
    answer: Union[BinaryAnswer, MarriageRegime, int] = Field(
        description="MUST be one of: 'Yes', 'No', 'Don't know', 'Not applicable', OR a property regime ('Separation of property', 'Partial community of property', etc.), OR a single number. Keep it SHORT - maximum 50 characters.",
        )
    legal_basis: Optional[str] = Field(
        default=None,
        description="The legal framework or laws that support this answer: Article number, law name, regulation name, policy name, etc."
        )
    additional_notes: Optional[str] = Field(
        default=None,
        description="Important caveats, recent changes, or regional variations, duration, amounts, percentages where applicable"
    )
    confidence_level: str = Field(
        description="Confidence level: High, Medium, or Low based on clarity of legal framework"
    )
    is_cached: Optional[bool] = Field(
        default=False,
        description="Whether this response came from cache"
    )


    def to_series(self) -> pd.Series:
        return pd.Series(self.model_dump())


class LegalReviewResponse(BaseModel):
    """Structured response for legal reviews of previous responses"""
    # survey_id: str = Field(description="The survey ID being analyzed")
    # country: Country = Field(description="The country being analyzed")
    # topic: Topic = Field(description="The topic being analyzed")
    # question: str = Field(description="The survey question being analyzed")
    same_as_previous: bool = Field(
        default=True,
        description="Whether the response is the same as the previous response",
        )
    confidence_level: str = Field(
        description="Confidence level: High, Medium, or Low based on clarity of legal framework"
    )
    new_legal_basis: Optional[str] = Field(
        default=None,
        description="The legal framework or laws that support the new answer: Article number, law name, regulation name, policy name, etc."
        )
    new_quantitative_details: Optional[str] = Field(
        default=None,
        description="The new quantitative details (duration, amounts, age, percentages where applicable)"
        )
    url_new_legal_basis: Optional[str] = Field(
        default=None,
        description="The URL of the source of the new legal basis if applicable"
        )


    def to_series(self) -> pd.Series:
        return pd.Series(self.model_dump())


class LegalBasisEvaluation(str, Enum):
    SAME = "Same"
    DIFFERENT = "Different"
    INCOMPLETE = "Incomplete"

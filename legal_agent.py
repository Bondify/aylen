"""
Simple Legal AI Agent using Pydantic AI
Provides consistent legal analysis across different countries
"""

import os
import yaml
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

# Configure Bedrock model with region using provider
bedrock_model = BedrockConverseModel(
    model_name="anthropic.claude-3-5-sonnet-20240620-v1:0",
    # model_name="meta.llama3-70b-instruct-v1:0",  # no access
    # model_name="amazon.nova-lite-v1:0",
    provider=BedrockProvider(region_name="us-east-1")
)

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

class Survey(BaseModel):
    """Survey question model"""
    id: str = Field(description="Unique identifier for the survey")
    question: str = Field(description="The legal question to analyze")
    criteria: str = Field(description="Detailed criteria for analysis")

def load_surveys() -> Dict[str, Survey]:
    """Load survey questions from YAML file"""
    try:
        with open('legal_surveys.yaml', 'r') as file:
            data = yaml.safe_load(file)
            surveys = {}
            for survey_id, survey_data in data['surveys'].items():
                surveys[survey_id] = Survey(**survey_data)
            return surveys
    except FileNotFoundError:
        raise FileNotFoundError("legal_surveys.yaml file not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing legal_surveys.yaml: {e}")


class LegalAnalysisResponse(BaseModel):
    """Structured response for legal queries with consistent criteria"""
    survey_id: str = Field(description="The survey ID being analyzed")
    country: Country = Field(description="The country being analyzed")
    question: str = Field(description="The survey question being analyzed")
    answer: str = Field(description="Direct answer to the legal question")
    legal_basis: str = Field(description="The legal framework or laws that support this answer")
    duration_or_amount: Optional[str] = Field(
        default=None, 
        description="Specific duration, amount, or quantitative details if applicable"
    )
    additional_notes: Optional[str] = Field(
        default=None,
        description="Important caveats, recent changes, or regional variations"
    )
    confidence_level: str = Field(
        description="Confidence level: High, Medium, or Low based on clarity of legal framework"
    )

class LegalQuery(BaseModel):
    """Input model for legal queries"""
    question: str = Field(description="The legal question to analyze")
    country: Country = Field(description="The country to analyze the law for")

# Create the Legal AI Agent
# legal_agent = Agent(
#     bedrock_model,
#     system_prompt="""You are a specialized Legal AI assistant that provides accurate legal information across different countries.

# Your role is to:
# 1. Analyze legal questions using consistent criteria across all countries
# 2. Provide structured, comparable responses regardless of the country
# 3. Focus on factual legal information, not legal advice
# 4. Be clear about limitations and recommend consulting local legal professionals

# Analysis Criteria (apply consistently across all countries):
# - Direct answer to the question (yes/no/conditional)
# - Legal basis (specific laws, regulations, or legal frameworks)
# - Quantitative details (duration, amounts, percentages where applicable)
# - Eligibility requirements (who qualifies, conditions to meet)
# - Important caveats or variations
# - Confidence level based on clarity of legal framework

# Important Guidelines:
# - Always specify the exact country being analyzed
# - Use current legal information (state if information might be outdated)
# - Distinguish between national laws and regional variations
# - Provide specific legal references when possible, the article number of the law if possible
# - Be honest about uncertainty and recommend professional consultation
# - Do not provide legal advice, only legal information

# Format your response using the structured format provided."""
# )

async def analyze_legal_query(question: str, country: Country, criteria: str) -> LegalAnalysisResponse:
    """
    Analyze a legal survey question for a specific country
    
    Args:
        survey_id: The ID of the survey question to analyze
        country: The country to analyze the law for
        
    Returns:
        Structured legal analysis response
    """
    # Create a specialized agent for this query with structured output using Bedrock
    structured_agent = Agent(
        bedrock_model,
        output_type=LegalAnalysisResponse,
        model_settings={'temperature': 0.2},
        system_prompt=f"""You are a specialized Legal AI assistant analyzing laws for {country.value}.

        Provide a structured analysis following these criteria:
        - Direct answer to the question (yes/no/conditional)
        - Legal basis (specific laws, regulations, or legal frameworks), the article number of the law if possible
        - Quantitative details (duration, amounts, percentages where applicable)
        - Eligibility requirements (who qualifies, conditions to meet)
        - Important caveats or variations
        - Confidence level based on clarity of legal framework

        Focus on factual legal information, not legal advice. Be clear about limitations and recommend consulting local legal professionals.

        {criteria}"""
    )
    
    # Run the agent with the structured query
    result = await structured_agent.run(
        f"Analyze this legal question for {country.value}: {question}"
    )
    
    return result.output


# Example usage function
async def compare_across_countries(question: str, countries: List[Country], criteria: str) -> List[LegalAnalysisResponse]:
    """
    Analyze the same legal survey question across multiple countries for comparison
    
    Args:
        survey_id: The ID of the survey question to analyze
        countries: List of countries to analyze
        
    Returns:
        List of structured responses for each country
    """
    results = []
    for country in countries:
        try:
            analysis = await analyze_legal_query(question, country, criteria)
            results.append(analysis)
        except Exception as e:
            print(f"Error analyzing {country.value}: {e}")
            continue
    
    return results

if __name__ == "__main__":
    import asyncio
    
    async def main():
        
        # Example: Analyze flexible work arrangements survey across different countries
        survey_id = "flexible_work_arrangements"
        survey = load_surveys()[survey_id]
        print(f"Analyzing Survey: {survey.question}")
        print("\n" + "="*50 + "\n")
        
        countries = [Country.CANADA]
        
        print(f"Analyzing across {len(countries)} countries...\n")
        
        results = await compare_across_countries(survey.question, countries, survey.criteria)
        
        for result in results:
            print(f"=== {result.country.value} ===")
            print(f"Survey: {result.survey_id}")
            print(f"Question: {result.question}")
            print(f"Answer: {result.answer}")
            print(f"Legal Basis: {result.legal_basis}")
            if result.duration_or_amount:
                print(f"Duration/Amount: {result.duration_or_amount}")
            print(f"Confidence: {result.confidence_level}")
            if result.additional_notes:
                print(f"Notes: {result.additional_notes}")
            print()
    
    # Run the example
    asyncio.run(main())
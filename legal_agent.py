"""
Simple Legal AI Agent using Pydantic AI
Provides consistent legal analysis across different countries
"""

import os
import yaml
import requests
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.models.openai import OpenAIModel

# Load API keys from YAML file
def load_api_keys():
    """Load API keys from api_keys.yaml file"""
    try:
        with open('api_keys.yaml', 'r') as file:
            keys = yaml.safe_load(file)
            return keys
    except FileNotFoundError:
        raise FileNotFoundError("api_keys.yaml file not found. Please create it with your API keys.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing api_keys.yaml: {e}")

# Load API keys
api_keys = load_api_keys()

# Available AI models
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
        "cost": "Low"
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
        "description": "Most capable OpenAI model",
        "cost": "Medium"
    },
    AIModel.GPT_3_5_TURBO: {
        "name": "GPT-3.5 Turbo",
        "provider": "OpenAI",
        "description": "Reliable and affordable",
        "cost": "Low"
    },
    AIModel.CLAUDE_3_5_SONNET: {
        "name": "Claude 3.5 Sonnet",
        "provider": "AWS Bedrock",
        "description": "Excellent for complex reasoning",
        "cost": "High"
    }
}

def get_ai_model(model_choice: AIModel = AIModel.GPT_5):
    """Get an AI model instance based on the choice"""
    if model_choice == AIModel.CLAUDE_3_5_SONNET:
        return BedrockConverseModel(
            model_name="anthropic.claude-3-5-sonnet-20240620-v1:0",
            provider=BedrockProvider(region_name="us-east-1")
        )
    else:
        # OpenAI models
        if 'openai_api_key' in api_keys:
            os.environ['OPENAI_API_KEY'] = api_keys['openai_api_key']
        else:
            raise ValueError("OpenAI API key not found in api_keys.yaml. Please add 'openai_api_key: your_api_key'")
        
        return OpenAIModel(model_name=model_choice.value)

def get_model_provider(model_choice: AIModel) -> str:
    """Get the provider type for a model (for temperature settings)"""
    return "bedrock" if model_choice == AIModel.CLAUDE_3_5_SONNET else "openai"

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

# Country to language mapping for web searches
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

def get_country_language(country: Country) -> tuple[str, str]:
    """Get the language name and code for a country"""
    return COUNTRY_LANGUAGES.get(country, ("English", "en"))

def search_web_for_legal_info(question: str, country: Country, criteria: str) -> str:
    """
    Search the web for legal information using Serper API
    
    Args:
        question: The legal question to search for
        country: The country to focus the search on
        criteria: The analysis criteria to help build search query
        
    Returns:
        Formatted search results as context string
    """
    try:
        # Get country language for search
        language_name, language_code = get_country_language(country)
        
        # Build search query in the country's language
        search_terms = {
            "en": f"legal law legislation {country.value} {question}",
            "es": f"ley legislación legal {country.value} {question}",
            "fr": f"loi législation juridique {country.value} {question}",
            "de": f"Gesetz Rechtsvorschrift legal {country.value} {question}",
            "ar": f"قانون تشريع قانوني {country.value} {question}",
        }
        
        query = search_terms.get(language_code, search_terms["en"])
        
        # Call Serper API
        headers = {
            'X-API-KEY': api_keys.get('serper_api_key', ''),
            'Content-Type': 'application/json'
        }
        
        payload = {
            'q': query,
            'gl': language_code,  # Geographic location
            'hl': language_code,  # Interface language
            'num': 5  # Number of results
        }
        
        response = requests.post('https://google.serper.dev/search', 
                               headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            
            # Format search results for context
            context_parts = ["=== WEB SEARCH RESULTS ==="]
            
            if 'organic' in results:
                for i, result in enumerate(results['organic'][:3], 1):
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    link = result.get('link', '')
                    
                    context_parts.append(f"\nSource {i}:")
                    context_parts.append(f"Title: {title}")
                    context_parts.append(f"Content: {snippet}")
                    context_parts.append(f"URL: {link}")
            
            context_parts.append("\n=== END WEB SEARCH RESULTS ===")
            return "\n".join(context_parts)
            
        else:
            print(f"Serper API error: {response.status_code}")
            return ""
            
    except Exception as e:
        print(f"Web search error: {e}")
        return ""

class LegalQuery(BaseModel):
    """Survey question model"""
    id: str = Field(description="Unique identifier for the survey")
    question: str = Field(description="The legal question to analyze")
    criteria: str = Field(description="Detailed criteria for analysis")


def load_survey() -> Dict[str, LegalQuery]:
    """Load survey questions from YAML file"""
    try:
        with open('legal_surveys.yaml', 'r') as file:
            data = yaml.safe_load(file)
            surveys = {}
            for survey_id, survey_data in data['surveys'].items():
                surveys[survey_id] = LegalQuery(**survey_data)
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


async def analyze_legal_query(question: str, country: Country, criteria: str, model_choice: AIModel = AIModel.GPT_5) -> LegalAnalysisResponse:
    """
    Analyze a legal survey question for a specific country with web search fallback
    
    Args:
        question: The legal question to analyze
        country: The country to analyze the law for
        criteria: The analysis criteria
        model_choice: The AI model to use for analysis
        
    Returns:
        Structured legal analysis response
    """
    # Get the AI model instance for this request
    ai_model = get_ai_model(model_choice)
    model_provider = get_model_provider(model_choice)
    
    # First pass: analyze without web search
    initial_agent = Agent(
        ai_model,
        output_type=LegalAnalysisResponse,
        model_settings={'temperature': 0.2} if model_provider == 'bedrock' else {},
        system_prompt=f"""You are a specialized Legal AI assistant analyzing laws for {country.value}.

        Provide a structured analysis following these criteria:
        - Direct answer to the question (yes/no/conditional)
        - Legal basis (specific laws, regulations, or legal frameworks, policies, etc.), 
        - Provide the article number of the law if possible
        - Quantitative details (duration, amounts, percentages where applicable)
        - Important caveats or variations
        - Confidence level based on clarity of legal framework (High/Medium/Low)

        Focus on factual legal information, not legal advice. Be clear about limitations.

        {criteria}"""
    )
    
    # Get initial analysis
    initial_result = await initial_agent.run(
        f"Analyze this legal question for {country.value}: {question}"
    )
    
    initial_response = initial_result.output
    
    # Check if we need web search (confidence is Medium or Low)
    if initial_response.confidence_level in ["Low"]:
        print(f"Low confidence detected for {country.value}, searching web...")
        
        # Search web for additional context
        web_context = search_web_for_legal_info(question, country, criteria)
        
        if web_context:  # Only re-analyze if we got web results
            # Second pass: analyze with web context
            enhanced_agent = Agent(
                ai_model,
                output_type=LegalAnalysisResponse,
                model_settings={'temperature': 0.2} if model_provider == 'bedrock' else {},
                system_prompt=f"""You are a specialized Legal AI assistant analyzing laws for {country.value}.

                Provide a structured analysis following these criteria:
                - Direct answer to the question (yes/no/conditional)
                - Legal basis (specific laws, regulations, or legal frameworks, policies, etc.), 
                - Provide the article number of the law if possible
                - Quantitative details (duration, amounts, percentages where applicable)
                - Important caveats or variations
                - Confidence level based on clarity of legal framework (High/Medium/Low)

                Focus on factual legal information, not legal advice. Be clear about limitations.
                Use the web search results below to enhance your analysis and improve accuracy.

                {criteria}

                {web_context}"""
            )
            
            # Get enhanced analysis with web context
            enhanced_result = await enhanced_agent.run(
                f"Analyze this legal question for {country.value} using both your knowledge and the web search results: {question}"
            )
            
            return enhanced_result.output
    
    # Return initial result if confidence is High or web search failed
    return initial_response


# Example usage function
async def compare_across_countries(question: str, countries: List[Country], criteria: str, model_choice: AIModel = AIModel.GPT_5) -> List[LegalAnalysisResponse]:
    """
    Analyze the same legal survey question across multiple countries for comparison
    
    Args:
        question: The legal question to analyze
        countries: List of countries to analyze
        criteria: Analysis criteria
        model_choice: The AI model to use for analysis
        
    Returns:
        List of structured responses for each country
    """
    results = []
    for country in countries:
        try:
            analysis = await analyze_legal_query(question, country, criteria, model_choice)
            results.append(analysis)
        except Exception as e:
            print(f"Error analyzing {country.value}: {e}")
            continue
    
    return results


async def chat_about_legal_response(
    message: str,
    original_response: LegalAnalysisResponse,
    conversation_history: List[Dict[str, str]] = None,
    model_choice: AIModel = AIModel.GPT_4O_MINI
) -> str:
    """
    Chat agent for follow-up questions about a specific legal analysis
    
    Args:
        message: User's follow-up question
        original_response: The original legal analysis to discuss
        conversation_history: Previous messages in this thread
        model_choice: AI model to use for the conversation
        
    Returns:
        Conversational response from the agent
    """
    ai_model = get_ai_model(model_choice)
    model_provider = get_model_provider(model_choice)
    
    # Build conversation history
    conversation_context = ""
    if conversation_history:
        for msg in conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            conversation_context += f"\n{role.upper()}: {content}"
    
    # Create system prompt with original legal response context
    system_prompt = f"""You are a helpful legal AI assistant having a conversation about a specific legal analysis.

        ORIGINAL LEGAL ANALYSIS CONTEXT:
        Country: {original_response.country.value}
        Survey: {original_response.survey_id}
        Question: {original_response.question}
        Answer: {original_response.answer}
        Legal Basis: {original_response.legal_basis}
        Confidence: {original_response.confidence_level}
        Additional Notes: {original_response.additional_notes or "None"}

        You are now having a follow-up conversation about this legal analysis. 

        CONVERSATION GUIDELINES:
        - Be conversational and helpful
        - Reference the original analysis when relevant
        - If you need more current information, indicate that you should search the web
        - Ask clarifying questions when the user's question is unclear
        - Provide practical insights and explanations
        - Stay focused on legal topics related to the original analysis
        - Be honest about limitations and suggest consulting legal professionals when appropriate

        CONVERSATION HISTORY:{conversation_context}

        Respond naturally to the user's follow-up question.
    """

    # Check if we should do a web search based on the message
    search_indicators = [
        "recent", "current", "latest", "new", "update", "changed", 
        "2024", "2025", "now", "today", "this year", "outdated", "old"
    ]
    
    should_search_web = any(indicator in message.lower() for indicator in search_indicators)
    
    web_context = ""
    if should_search_web:
        print(f"🔍 Searching web for: {message}")
        web_context = search_web_for_legal_info(
            message, 
            original_response.country, 
            f"Follow-up question about: {original_response.question}"
        )
        if web_context:
            system_prompt += f"\n\nCURRENT WEB SEARCH RESULTS:\n{web_context}"
    
    # Create conversational agent
    agent = Agent(
        ai_model,
        output_type=str,  # Free-form conversational response
        model_settings={'temperature': 0.3} if model_provider == 'bedrock' else {},  # Slightly more creative
        system_prompt=system_prompt
    )
    
    # Get response
    result = await agent.run(message)
    return result.output


if __name__ == "__main__":
    import asyncio
    
    async def main():
        
        # Example: Analyze flexible work arrangements survey across different countries
        survey_id = "flexible_work_arrangements"
        survey = load_survey()[survey_id]
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
            print(f"Confidence: {result.confidence_level}")
            if result.additional_notes:
                print(f"Notes: {result.additional_notes}")
            print()
    
    # Run the example
    asyncio.run(main())
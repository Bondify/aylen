"""
Simple Legal AI Agent using Pydantic AI
Provides consistent legal analysis across different countries
"""

from typing import List, Dict
from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.builtin_tools import UrlContextTool
from backend.data_objects import AIModel, Country, LegalAnalysisResponse, Topic
from pydantic_ai.models.anthropic import AnthropicModel

from dotenv import load_dotenv
from backend.tools.utils import load_survey


load_dotenv()


def build_system_prompt(country: Country, criteria: str, topic: Topic) -> str:
    return f"""You are a specialized Legal AI assistant analyzing laws for {country.value} and the topic {topic.value}.

        Provide a structured analysis following these criteria:
        - Direct answer to the question (Yes, No, don't know, not applicable, short answer (separation of property, , divorce, etc,), a number)
        - Legal basis (specific laws, regulations, or legal frameworks, policies, etc.), 
        - Provide the article number of the law if possible
        - Quantitative details (duration, amounts, age, percentages where applicable)
        - Important caveats or variations
        - Confidence level based on clarity of legal framework (High/Medium/Low)
        - Topic: The topic to analyze the law for

        Focus on factual legal information, not legal advice. Be clear about limitations.

        {criteria}"""


def generate_1_shot_agent(llm: AIModel, country: Country, criteria: str, topic: Topic) -> Agent:
    "Entry agent that tries to answer the question in one-shot"
    
    return Agent(
        llm,
        output_type=LegalAnalysisResponse,
        model_settings={'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        system_prompt=build_system_prompt(country, criteria, topic)
    )


def generate_web_search_agent(llm: AIModel, country: Country, criteria: str, topic: Topic) -> Agent:
    return Agent(
        llm,
        output_type=LegalAnalysisResponse,
        model_settings={'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        system_prompt=build_system_prompt(country, criteria, topic),
        builtin_tools=[WebSearchTool()],
        max_steps=5
    )


def generate_document_search_agent(llm: AIModel, country: Country, criteria: str, topic: Topic) -> Agent:
    "Agent that searches the documents for the legal information, only available for google models"
    return Agent(
        llm,
        output_type=LegalAnalysisResponse,
        system_prompt=build_system_prompt(country, criteria, topic),
        builtin_tools=[UrlContextTool()],
        max_steps=5
    )


async def analyze_legal_query(question: str, country: Country, criteria: str, topic: Topic, llm: AIModel = AIModel.GPT_5) -> LegalAnalysisResponse:
    """
    Analyze a legal survey question for a specific country with web search fallback
    
    Args:
        question: The legal question to analyze
        country: The country to analyze the law for
        criteria: The analysis criteria
        topic: The topic to analyze the law for
        llm: The AI model to use for analysis
        
    Returns:
        Structured legal analysis response
    """    
    # First pass: analyze without web search
    initial_agent = generate_1_shot_agent(llm, country, criteria, topic)
    
    # Get initial analysis
    initial_result = await initial_agent.run(
        f"Analyze this legal question for {country.value} under the topic '{topic.value}': {question}"
    )
    
    # Debug info
    debug_info = {
        'messages': initial_result.all_messages(),
        'usage': initial_result.usage(),  # Token usage
        'model': llm.model_name,
        'timestamp': initial_result.timestamp()
    }
    
    return {"response": initial_result.output, "debug_info": debug_info}


if __name__ == "__main__":
    import asyncio
    
    async def main():
        
        # Example: Analyze flexible work arrangements survey across different countries
        survey_id = "flexible_work_arrangements"
        survey = load_survey()[survey_id]
        print(f"Analyzing Survey: {survey.question}")
        print("\n" + "="*50 + "\n")
        
        country = Country.CANADA
        
        results = await analyze_legal_query(survey.question, country, survey.criteria, Topic.WORKPLACE)
        
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
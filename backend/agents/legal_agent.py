"""
Simple Legal AI Agent using Pydantic AI
Provides consistent legal analysis across different countries
"""

from typing import List, Dict, Type
from pydantic import BaseModel
from pydantic_ai import Agent, WebSearchTool
from pydantic_ai.builtin_tools import UrlContextTool
from pydantic_ai.models.google import GoogleModel
from backend.data_objects import AIModel, Country, LegalAnalysisResponse, LegalReviewResponse, Topic
from pydantic_ai.models.anthropic import AnthropicModel
from backend.cache_service import cache

from dotenv import load_dotenv
from backend.tools.utils import load_survey


load_dotenv()


def prompt_from_scratch(country: Country, topic: Topic) -> str:
    return f"""You are a specialized Legal AI assistant analyzing laws for {country.value} and the topic {topic.value}.

        Provide a structured analysis following these criteria:
        - Direct answer to the question (Yes, No, don't know, not applicable, short answer (separation of property, divorce, etc), a number)
        - Legal basis (specific laws, regulations, or legal frameworks, policies, etc.), 
        - Provide the article number of the law if possible
        - Quantitative details (duration, amounts, age, percentages where applicable)
        - Confidence level based on clarity of legal framework: High/Medium/Low
        - Topic: The topic to analyze the law for

        Focus on factual legal information, not legal advice. Be clear about limitations.
        """


def prompt_reviewer_assistant(country: Country, topic: Topic) -> str:
    return f"""You are a legal consultant at "Women Business and the Law" specialized in {country.value} and the topic {topic.value}.
        You will be given a legal question with its response and legal basis as of the year 2024.
        Assume that the response from 2024 is correct as of 2024.
        Your task is to review the response and check if it is still correct as of November 2025.
        To do this, you can use the web search tool to check the latest laws and regulations.
        If you find that the response is no longer correct you need to justify it with a legal basis that is newer than the one
        referenced in the answer or the legal basis of the year 2024.
        Provide a structured analysis following these criteria:
        - Still correct: Yes or No
        - Confidence level based on clarity of legal framework: High/Medium/Low
        - If the answer is "No":
            - Then, provide the new legal basis that is newer than the one referenced with the year 2024 (specific laws, regulations, or legal frameworks, policies, etc.),
            - Then, provide the article number of the law if possible
            - Then, provide the new quantitative details (duration, amounts, age, percentages where applicable)
            - Then, provide the URL of the source of the new legal basis if applicable
        Focus on factual legal information, not legal advice. Be clear about limitations.
        """


def generate_1_shot_agent(llm: AIModel, country: Country, topic: Topic) -> Agent:
    "Entry agent that tries to answer the question in one-shot"
    
    return Agent(
        llm,
        output_type=LegalAnalysisResponse,
        model_settings={'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        system_prompt=build_system_prompt(country, topic)
    )


def generate_web_search_agent(
    llm: AIModel,
    country: Country, 
    topic: Topic,
) -> Agent:

    params = {
        'model_settings': {'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        'system_prompt': prompt_reviewer_assistant(country, topic),
        'builtin_tools': [WebSearchTool()],
    }
    is_gemini = isinstance(llm, GoogleModel)
    if not is_gemini:
        # params['output_type'] = LegalAnalysisResponse
        params['output_type'] = LegalReviewResponse
    return Agent(llm, **params)


def generate_document_search_agent(llm: AIModel, country: Country, topic: Topic) -> Agent:
    "Agent that searches the documents for the legal information, only available for google models"
    return Agent(
        llm,
        output_type=LegalAnalysisResponse,
        system_prompt=build_system_prompt(country, topic),
        builtin_tools=[UrlContextTool()],
        # max_steps=5
    )


async def analyze_legal_query(
    question: str,
    country: Country,
    topic: Topic,
    previous_response: str,
    previous_legal_basis: str,
    yes_if: str=None,
    no_if: str=None,
    llm: AIModel = AIModel.GPT_5
) -> LegalReviewResponse:
    """
    Analyze a legal survey question for a specific country with web search fallback
    
    Args:
        question: The legal question to analyze
        country: The country to analyze the law for
        topic: The topic to analyze the law for
        yes_if: The yes if criteria
        no_if: The no if criteria
        llm: The AI model to use for analysis
        
    Returns:
        Structured legal analysis response
    """
    # Build the full prompt (system + user message)
    system_prompt = prompt_reviewer_assistant(country, topic)
    user_message = f"""
        Analyze this legal question for {country.value} under the topic '{topic.value}': {question}.
        The previous response was: "{previous_response}".
        And the previous legal basis was: "{previous_legal_basis}".
    """
    if yes_if:
        user_message += f'\nAnswer YES IF: "{yes_if}".'
    if no_if:
        user_message += f'\nAnswer NO IF: "{no_if}".'
    full_prompt = f"{system_prompt}\n\n{user_message}"
    
    # Check cache first
    cached_response = cache.get_cached_response(full_prompt, llm.model_name)
    if cached_response is not None:
        # Return cached response
        return {"response": cached_response, "debug_info": {"cached": True, "model": llm.model_name}}
    
    # Cache miss - make the API call
    initial_agent = generate_web_search_agent(llm, country, topic)

    # Get initial analysis
    initial_result = await initial_agent.run(user_message)
    
    # Debug info
    debug_info = {
        'messages': initial_result.all_messages(),
        'usage': initial_result.usage(),  # Token usage
        'model': llm.model_name,
        'timestamp': initial_result.timestamp(),
        'cached': False
    }

    # Check the format of the response
    if isinstance(initial_result.output, LegalReviewResponse):
        response = initial_result.output
    else:
        # Format the response
        formatter = generate_formatting_agent(llm, country, topic)
        formatted_result = await formatter.run(
            f"Format this legal analysis for the question '{question}':\n\n{initial_result.output}"
        )
        response = formatted_result.output
    
    # Store in cache
    cache.store_response(full_prompt, llm.model_name, response, question, country, topic)
    
    return {"response": response, "debug_info": debug_info}


def generate_formatting_agent(llm: AIModel, country: Country, topic: Topic) -> Agent:
    """Agent to format raw text into LegalAnalysisResponse structure"""
    return Agent(
        llm,
        output_type=LegalReviewResponse,
        model_settings={'temperature': 0.0} if isinstance(llm, AnthropicModel) else {},
        system_prompt=f"""You are a legal response formatter. 
        
        Parse the provided legal analysis text into a structured format for {country.value} and topic {topic.value}.

        Extract:
        - answer: Must be 'Yes', 'No', 'Don't know', 'Not applicable', a property regime, or a number (max 50 chars)
        - legal_basis: Article numbers, law names, regulations, policies mentioned
        - additional_notes: Caveats, variations, durations, amounts, percentages
        - confidence_level: High, Medium, or Low

        Be precise and keep the answer field SHORT."""
    ) 


# if __name__ == "__main__":
#     import asyncio
    
#     async def main():
        
#         # Example: Analyze flexible work arrangements survey across different countries
#         survey_id = "flexible_work_arrangements"
#         survey = load_survey()[survey_id]
#         print(f"Analyzing Survey: {survey.question}")
#         print("\n" + "="*50 + "\n")
        
#         country = Country.CANADA
        
#         results = await analyze_legal_query(survey.question, country, survey.yes_if, survey.no_if, Topic.WORKPLACE)
        
#         for result in results:
#             print(f"=== {result.country.value} ===")
#             print(f"Survey: {result.survey_id}")
#             print(f"Question: {result.question}")
#             print(f"Answer: {result.answer}")
#             print(f"Legal Basis: {result.legal_basis}")
#             print(f"Confidence: {result.confidence_level}")
#             if result.additional_notes:
#                 print(f"Notes: {result.additional_notes}")
#             print()
    
#     # Run the example
#     asyncio.run(main())
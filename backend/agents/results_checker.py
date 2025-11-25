

from typing import Tuple
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from backend.data_objects import AIModel, Country, LegalBasisEvaluation


def answer_evaluator_agent(llm: AIModel) -> Agent:
    "Agent that decides if two responses to the same question are the same"

    system_prompt = f"""
    You are a legal analyst that is given two responses to the same question.
    The responses come from different sources, so they can have different styles and formats, even if the 
    answer is conceptually the same.
    Your task is to determine if the responses are the same.
    If they are the same, return True.
    If they are different, return False.
    
    Examples:
    Example Q 1: Does the law grant spouses equal administrative authority over assets during marriage?
    Response 1: Yes
    Response 2: Yes, with important distinctions based on asset type.
    You should return True because the answers are conceptually the same.
    Example Q 2: What is the default marital property regime?
    Response 1: Separation of property
    Response 2: Separation of property (each spouse holds property in their own name by default); there is no automatic community property regime.
    You should return True because the answers are conceptually the same.
    Example Q 3: Paid parental leave in days for the mother?
    Response 1: No
    Response 2: Likely 12 weeks (84 days) maternity leave, subject to confirmation
    You should return False because the answers are different.
    Example Q 4: How long is the paid parental leave for the mother?
    Response 1: 84 
    Response 2: Likely 12 weeks maternity leave.
    You should return True because 84 days is equivalent to 12 weeks.
    """
    return Agent(
        llm,
        output_type=bool,
        model_settings={'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        system_prompt=system_prompt
    )


async def eval_answer(question: str, response_1: str, response_2: str, llm: AIModel = AIModel.GPT_4O_MINI) -> bool:
    """
    Evaluate if two responses to the same question are the same
    
    Args:
        question: The legal question to analyze
        response_1: The first response to evaluate
        response_2: The second response to evaluate
        llm: The AI model to use for evaluation
    Returns:
        True if the responses are the same, False otherwise.
    """    
    eval_result_agent = answer_evaluator_agent(llm)
    eval_result = await eval_result_agent.run(
        f"Evaluate if the following responses to the question '{question}' are the same: {response_1} and {response_2}"
    )
    return eval_result.output


def legal_basis_evaluator_agent(llm: AIModel) -> Agent:
    "Agent that decides if two legal bases that support the same answer to the same question are the same"

    system_prompt = f"""
    You are a legal analyst that is given two legal bases that support the same answer to the same question.
    The source of the legal bases are different, so they can have different styles and formats, even if they
    refer to the same law or regulation.
    Your task is to determine if the legal bases are the same.
    If they are the same, return SAME.
    If they are different, return DIFFERENT.
    If the first legal bases indicates more articles/laws than the second, return INCOMPLETE.
    
    Examples:
    Example Q 1: Is paid leave of at least 14 weeks available to mothers?
    Legal basis 1: Labor Code of Antigua and Barbuda (Amendment) Act 2022, Sec.3; Social Security (Benefits) (Maternity) (Amendment) Regulations, Sec. 3; Social Security (Benefits) (Maternity) Regulations, Sec. 10; Labor Code of Antigua and Barbuda (Amendment) Act, 1998, Sec. 11
    Legal basis 2: Employment (Maternity Leave) Act, 1996
    You should return DIFFERENT because they refer to different laws and regulations.

    Example Q 2: Is dismissal of pregnant workers prohibited?
    Legal basis 1: Code du Travail, Art. L1225-4
    Legal basis 2: Code du travail, Article L1225-4
    You should return SAME because the legal bases refer to the same article, even if they are formatted differently.

    Example Q 3: Does the law grant spouses equal administrative authority over assets during marriage?
    Legal basis 1: Code civil, Arts. 1421, 1422, 1424 et 1425
    Legal basis 2: French Civil Code, Article 1421
    You should return INCOMPLETE because the first legal basis indicates more articles/laws than the second.
    """
    return Agent(
        llm,
        output_type=LegalBasisEvaluation,
        model_settings={'temperature': 0.2} if isinstance(llm, AnthropicModel) else {},
        system_prompt=system_prompt
    )


async def eval_legal_basis(question: str, country: str, legal_basis_1: str, legal_basis_2: str, llm: AIModel = AIModel.GPT_4O_MINI) -> LegalBasisEvaluation:
    """
    Evaluate if two legal bases that support the same answer to the same question are the same
    
    Args:
        question: The legal question to analyze
        legal_basis_1: The first legal basis to evaluate
        legal_basis_2: The second legal basis to evaluate
        llm: The AI model to use for evaluation
    Returns:
        - SAME if the legal bases are the same, 
        - DIFFERENT if they are different,
        - INCOMPLETE if the first legal basis indicates more articles/laws than the second.
    """    
    eval_result_agent = legal_basis_evaluator_agent(llm)
    eval_result = await eval_result_agent.run(
        f"""
        Evaluate if the following legal bases in {country} that support the same answer to the question '{question}' are the same:
        {legal_basis_1}
        {legal_basis_2}
        """
    )
    return eval_result.output
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")

gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=GOOGLE_API_KEY
)

SEARCH_PROMPT = """
You are an AI marketing strategist.

Based on the business information provided, generate between 5 and 12 **high-quality web search questions** 
that would help gather research insights.

Company Name: {company_name}
Product Description: {product_description}
Target Audience: {target_audience}
Tone of Voice: {tone}

IMPORTANT:
- Return ONLY a JSON array of strings.
- Do NOT include markdown (```) or any extra text.
- The JSON array should look like this: ["Question 1", "Question 2", ...].

Generate questions that:
- Are relevant to the business
- Will enhance marketing strategies
- Are search-engine friendly
"""

prompt = PromptTemplate(
    input_variables=["company_name", "product_description", "target_audience", "tone"],
    template=SEARCH_PROMPT,
)

async def generate_search_questions(company_name, product_description, target_audience, tone):
    final_prompt = prompt.format(
        company_name=company_name,
        product_description=product_description,
        target_audience=target_audience,
        tone=tone
    )

    # IMPORTANT: async call
    response = await gemini.ainvoke([HumanMessage(content=final_prompt)])

    import json
    try:
        questions = json.loads(response.content)
        return questions
    except Exception as e:
        print("JSON parse error:", e, "Raw response:", response.content)
        return []

ANSWER_PROMPT = """
You are an AI marketing strategist.

Provide a detailed, high-quality answer to the following research question:

Question: {question}

Company Name: {company_name}
Product Description: {product_description}
Target Audience: {target_audience}
Tone of Voice: {tone}

IMPORTANT:
- Return ONLY the answer text.
- Do not include any markdown formatting or extra commentary.
"""

async def generate_answer(question, company_name, product_description, target_audience, tone):
    from langchain.prompts import PromptTemplate
    from langchain.schema import HumanMessage

    prompt = PromptTemplate(
        input_variables=["question", "company_name", "product_description", "target_audience", "tone"],
        template=ANSWER_PROMPT,
    )

    final_prompt = prompt.format(
        question=question,
        company_name=company_name,
        product_description=product_description,
        target_audience=target_audience,
        tone=tone
    )

    response = await gemini.ainvoke([HumanMessage(content=final_prompt)])
    return response.content.strip()

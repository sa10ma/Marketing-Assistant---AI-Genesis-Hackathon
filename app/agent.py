import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage

GOOLGE_API_KEY = os.environ.get("GEMINI_API_KEY")
# Initialize Gemini model
gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=GOOLGE_API_KEY
)

# Custom prompt template for marketing agent
MARKETING_PROMPT = """
You are a professional marketing strategist AI for the company: {company_name}.
Your job is to answer the user's request with actionable, creative, and structured marketing insights.

User message:
{user_message}

Respond professionally and concisely.
"""

prompt = PromptTemplate(
    input_variables=["company_name", "user_message"],
    template=MARKETING_PROMPT
)

async def generate_ai_response(company_name: str, user_message: str):
    """Generate marketing response using Gemini through LangChain."""
    
    final_prompt = prompt.format(
        company_name = company_name,
        user_message = user_message
    )
    
    response = gemini.invoke([HumanMessage(content=final_prompt)])
    return response.content

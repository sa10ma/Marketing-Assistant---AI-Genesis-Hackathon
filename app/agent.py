import os
import json
from app.qdrant_rag import retrieve_data
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")

gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=GOOGLE_API_KEY
)


async def generate_search_questions(company_name, product_description, target_audience, tone):
    print("\n\nhi from seach agent\n\n")
    SEARCH_PROMPT = """
        You are an AI marketing strategist with the ability to request and leverage user-specific memory 
        (if available). Your goal is to generate between 2 and 5 high-quality web search questions that 
        support strong marketing research.

        Business Inputs:
        Company Name: {company_name}
        Product Description: {product_description}
        Target Audience: {target_audience}
        Tone of Voice: {tone}

        Before generating questions:
        - Check whether any key business information is missing or unclear.
        - If something important is missing (e.g., company name, target audience specifics, product positioning, goals),
        respond with a JSON object of the form:
        {
            "need_more_info": true,
            "questions": ["Ask the user this clarification question..."]
        }
        Do NOT generate search questions yet.

        If all required information is present:
        - Suggest useful memory items (such as business name, target audience, tone), using the field:
        "memory_suggestions": ["item1", "item2"]
        - Then generate the search questions.

        OUTPUT FORMAT (strict):
        Return ONLY a JSON object, no markdown and no extra commentary.

        If all information is available, return:
        {
        "need_more_info": false,
        "memory_suggestions": ["example item 1", "example item 2"],
        "search_questions": ["Question 1", "Question 2", ...]
        }

        Guidelines for search questions:
        - They must be actionable and research-oriented.
        - They must be relevant to the business.
        - They must enhance strategic marketing.
        - They should be search-engine-friendly.
    """

    prompt = PromptTemplate(
    input_variables=["company_name", "product_description", "target_audience", "tone"],
    template=SEARCH_PROMPT,
    )

    final_prompt = prompt.format(
        company_name=company_name,
        product_description=product_description,
        target_audience=target_audience,
        tone=tone
    )

    # IMPORTANT: async call
    response = await gemini.ainvoke([HumanMessage(content=final_prompt)])

    try:
        questions = json.loads(response.content)
        return questions
    except Exception as e:
        print("JSON parse error:", e, "Raw response:", response.content)
        return []



async def generate_answer(question, company_name, product_description, target_audience, tone):

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

async def generate_content_with_rag(user_id: int, user_request: str):
    """
    Generate content for the user using RAG knowledge from Qdrant.
    If no relevant knowledge, generate content anyway.
    """
    # 1️⃣ Retrieve relevant data from RAG
    retrieved = retrieve_data(user_id=user_id, query=user_request, top_k=5)
    
    # 2️⃣ Combine retrieved knowledge into context
    context = "\n".join([item.get("text", "") + "\nAnswer: " + item.get("answer", "") for item in retrieved])

    if not context:
        context = "No relevant previous data found. Generate content based on general knowledge."

    # 3️⃣ Build prompt for Gemini
    prompt = f"""
        You are a marketing expert AI.

        User request:
        {user_request}

        Relevant previous knowledge (from RAG):
        {context}

        Write a high-quality marketing output based on the request.
        If no relevant data is available, generate the best answer you can.
        Give your output in plain text and emojis. Do not use markups.
        """

    # 4️⃣ Generate AI response
    response = await gemini.ainvoke([HumanMessage(content=prompt)])
    return response.content

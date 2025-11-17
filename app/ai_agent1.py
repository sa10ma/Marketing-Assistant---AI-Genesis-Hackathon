from langchain.chains import LLMChain
from langchain.prompts.chat import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def generate_marketing_questions(profile):
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.7
    )

    prompt = ChatPromptTemplate.from_template("""
        You are a senior marketing strategist.

        Using this business profile:

        Company Name: {company_name}
        Product/Service: {product_description}
        Target Audience: {target_audience}
        Tone of Voice: {tone_of_voice}

        Generate **10 insightful marketing discovery questions** that help clarify
        the strategy before producing marketing content.

        Return only the questions, numbered 1–10.
    """)

    chain = LLMChain(prompt=prompt, llm=llm)

    return chain.run({
        "company_name": profile.company_name,
        "product_description": profile.product_description,
        "target_audience": profile.target_audience,
        "tone_of_voice": profile.tone_of_voice
    })

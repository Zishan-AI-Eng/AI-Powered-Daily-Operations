import os
from groq import Groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()  # Load environment variables from .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# llm = ChatGoogleGenerativeAI(
#     model='gemini-25-flash',
#     api_key=GOOGLE_API_KEY,
#     temperature=0.2
#     ).bind(response_format={'type':'json_object'})



llm = ChatGroq(
    model='openai/gpt-oss-20b',
    api_key=GROQ_API_KEY,
    temperature=0.2
    ).bind(response_format={'type':'json_object'})

system_template = """
You are a data analyst. You will be provided with CRM data from HubSpot, including candidates (contacts) and jobs (deals). Your task is to analyze this data and provide insights, summaries, or any requested information based on the user's queries.
You will receive the data in JSON format. Please ensure that your responses are clear, concise,
    and structured. If you are asked to provide a summary, focus on key metrics, trends, and actionable insights. If you are asked specific questions, provide direct answers based on the data provided.
   
   You must output ONLY a valid JSON object with the following structure:
{{
  "summary": "Short summary of the comparison",
  "exceptions": ["List of missing details, e.g., phone number found in email but missing in CRM"],
  "action_items": ["What Hasan needs to update"]
}}
"""
    
human_template = """
You will be provided with CRM data in JSON format. Please analyze the data and provide insights,
    summaries, or any requested information based on the user's queries. Ensure that your responses are clear, concise, and structured. If you are asked to provide a summary, focus on key metrics, trends, and actionable insights. If you are asked specific questions, provide direct answers based on the data provided.
    
    CRM Data:
    {crm_data}
    
    Email Draft:
    {email_draft}
    """
    
prompt = ChatPromptTemplate.from_messages([
    ("system", system_template),
    ("human", human_template)
])


parser = StrOutputParser()

chain = prompt | llm | parser

def generate_daily_brief(crm_data, email_draft):
    response = chain.invoke({
        "crm_data": crm_data,
        "email_draft": email_draft,
    })

    return response


import json

# --- TESTING BLOCK ---
if __name__ == "__main__":
    # 1. Dummy CRM Data (Jo Pydantic se aayega)
    dummy_crm_data = {
        "candidates": [
            {"name": "AYAN MARWAT", "email": "marwtatking2@gmail.com", "phone_number": None},
            {"name": "ATIF KING", "email": "marwtatking1@gmail.com", "phone_number": None}
        ],
        "jobs": [
            {"id": "348860320482", "job_title": "FIRST CLIENT", "stage": "appointmentscheduled"}
        ]
    }

    # 2. Dummy Email Data
    dummy_email_draft = """
    Email 1: Hi Hasan, please update Ayan Marwat's phone number to 0300-1234567.
    Email 2: Atif King's interview for FIRST CLIENT is confirmed for tomorrow.
    """

    print("Groq AI is analyzing data... Please wait.\n")
    
    # 3. Function ko call karein aur dictionaries ko string/JSON format mein pass karein
    result = generate_daily_brief(
        crm_data=json.dumps(dummy_crm_data, indent=2), 
        email_draft=dummy_email_draft
    )
    
    print("--- AI DAILY BRIEF (JSON OUTPUT) ---")
    print(result)
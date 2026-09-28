import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(
    model=os.getenv("AI_MODEL", "gemini-2.5-flash"),
    contents="안녕, 한 줄로 자기소개 해줘.",
)
print(response.text)

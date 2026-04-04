from openai import OpenAI
from config import GROQ_API_KEY

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

MODEL = "openai/gpt-oss-120b"


FALLBACK_MODEL = "llama-3.3-70b-versatile"

def chat(prompt: str, system: str = "You are a football expert. Answer factually and concisely.", max_tokens: int = 1024) -> str:
    for model in [MODEL, FALLBACK_MODEL]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system + " Use plain markdown only: bullet points, bold, headings. Never use HTML tags like <br>. Never use markdown tables."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            finish = response.choices[0].finish_reason
            print(f"[LLM] model={model}, finish_reason={finish}, content_len={len(content) if content else 0}")
            if content:
                return content
            print(f"[LLM] Empty content from {model}, trying fallback...")
        except Exception as e:
            print(f"[LLM] Error from {model}: {e}")
    return "Sorry, I couldn't answer that question right now."

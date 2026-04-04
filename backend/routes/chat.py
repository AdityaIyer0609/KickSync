from fastapi import APIRouter
from llm import chat

router = APIRouter()


@router.post("/chat")
def chat_endpoint(query: str):
    response = chat(query)
    return {"response": response}

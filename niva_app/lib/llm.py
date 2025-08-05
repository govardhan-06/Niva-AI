import os
from sklearn.metrics.pairwise import cosine_similarity
from pydantic import BaseModel
from google import genai
from typing import Iterable, Optional, List
import json
import numpy as np

gemini_client=genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

def get_similarity(text1, text2):
    embeddings1 = text1 and create_embedding(text1)
    embeddings2 = text2 and create_embedding(text2)
    if embeddings1 and embeddings2:
        return cosine_similarity([embeddings1], [embeddings2])[0][0]
    else:
        return 0.0

def create_embedding(input, model="gemini-embedding-exp-03-07"):
    try:
        embedding = gemini_client.models.embed_content(
            model=model,
            contents=[input]
        )
        # Extract values from ContentEmbedding object
        if embedding and embedding.embeddings:
            return embedding.embeddings[0].values
        return None
    except Exception as e:
        print(f"Error creating embedding: {e} for input: {input}")
        return None


def llm(messages, _class: BaseModel, max_tokens: int = None, model: str = "gemini-2.0-flash"):
    response = gemini_client.models.generate_content(
        model=model,
        contents=[messages[0]["content"]],
        config={
            "response_mime_type": "application/json",
            "response_schema": _class,
        },
    )
    print(response.text)
    return response.text

def summarize_conversation(messages: list[dict], agent_name: str) -> str:
    conversation_text = ""

    for message in messages:
        conversation_text += f"{message['role'].replace('user','caller')}: {message['content']}\n"


    prompt = f"""
        Summarize the conversation in 2-3 sentences. Summarize in this format in the first person: `Hi there, this is {agent_name}. A caller needs assistance with ... I will connect you to the caller now.`
        ```
        {conversation_text}
        ```
    """
    print(f"Summarizing conversation:\n{prompt}")

    class Summary(BaseModel):
        summary: str

    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
        config={
            "response_mime_type": "application/json",
            "response_schema": Summary,
        },
    )
    print(response.text)
    return response.text
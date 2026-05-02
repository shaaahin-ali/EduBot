"""
RAG Engine v2 — Context-aware recommendation generation.

Combines retrieval with slot-filling and conversational prompting
to deliver personalized course recommendations.
"""

from __future__ import annotations
import json
import os
import faiss
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer

from config import GROQ_API_KEY, LLM_MODEL

_embedder: SentenceTransformer | None = None
_index: faiss.IndexFlatL2 | None = None
_chunks: list[str] = []
_client: Groq | None = None

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "course_catalog.json")

def _course_to_text(course: dict) -> str:
    return (
        f"Course: {course['name']}\n"
        f"Target Audience: {course['target']}\n"
        f"Duration: {course['duration']}\n"
        f"Fee: {course['fee']}\n"
        f"Schedule: {course['schedule']}\n"
        f"Highlights: {course['highlights']}"
    )

def init_rag() -> None:
    global _embedder, _index, _chunks, _client
    print("[rag_engine] Loading sentence-transformer model locally…")
    _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print(f"[rag_engine] Reading catalog from {CATALOG_PATH}")
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    _chunks = [_course_to_text(c) for c in catalog]
    print(f"[rag_engine] Embedding {len(_chunks)} course chunks locally…")

    embeddings = _embedder.encode(_chunks, convert_to_numpy=True).astype("float32")
    dim = embeddings.shape[1]
    _index = faiss.IndexFlatL2(dim)
    _index.add(embeddings)

    _client = Groq(api_key=GROQ_API_KEY)
    print(f"[rag_engine] FAISS index ready — {_index.ntotal} vectors, dim={dim}")

def retrieve(query: str, top_k: int = 2) -> list[str]:
    if _embedder is None or _index is None:
        return []
    query_vec = _embedder.encode([query], convert_to_numpy=True).astype("float32")
    _, indices = _index.search(query_vec, top_k)
    return [_chunks[i] for i in indices[0] if i < len(_chunks)]

def answer(user_message: str, session: dict, sentiment: str) -> str:
    """
    Generate a personalized answer using context memory and sentiment.
    """
    if _client is None:
        return "I'm having trouble connecting to my knowledge base right now. Please try again!"

    context_chunks = retrieve(user_message)
    context_block = "\n\n---\n\n".join(context_chunks)
    
    # Inject personality and context into the system prompt
    name_str = f"The student's name is {session['name']}." if session.get('name') else ""
    history_str = f"Their known interests: {', '.join(session['interests'])}." if session.get('interests') else ""
    
    system_prompt = f"""
You are EduBot, an expert admissions counsellor at EduBot Academy.
{name_str} {history_str}
The user is currently feeling: {sentiment}

Your goal is to provide a highly conversational, personalized answer using ONLY the course catalog info provided below.

Rules:
1. Don't just dump information. Explain *why* it fits them.
2. If they seem confused/indecisive, offer a simple A/B choice.
3. If they seem excited, encourage action (e.g., "Ready to book a demo?").
4. Keep it under 6 sentences. Use formatting (bullet points, bold text).
5. Address them by name if you know it.
6. NEVER mention that you are an AI or using context chunks.

### Course Catalog Data:
{context_block}
"""

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=300,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[rag_engine] Groq error: {e}")
        return "Sorry, I'm having trouble looking that up. Please try again! 🙏"

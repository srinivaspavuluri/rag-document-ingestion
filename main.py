from typing import Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from rag_core import run_rag


app = FastAPI(
    title="RAG API",
    description=("A grounded question-answering API using PostgreSQL, pgvector and Ollama."),
    version="1.0.0"
)


# --------------------------------------------------
# Request model
# --------------------------------------------------
class AskQuestion(BaseModel):
    question: str



# --------------------------------------------------
# Response models
# --------------------------------------------------
class SourceResponse(BaseModel):
    chunk_id: int
    document_id: int
    text: str
    distance: float
    metadata: dict[str, Any] | None = None

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceResponse]



# --------------------------------------------------
# Health check
# --------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "Healthy"
    }



# --------------------------------------------------
# RAG endpoint
# --------------------------------------------------
@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskQuestion):
    try:
        results = run_rag(request.question)
        return results
    
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        # Keep the detailed error in server logs.
        print(
            "RAG processing failed:",
            repr(error),
        )

        # Do not expose internal details to API users.
        raise HTTPException(
            status_code=500,
            detail="RAG processing failed.",
        ) from error


    

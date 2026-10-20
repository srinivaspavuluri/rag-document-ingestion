import os

import ollama
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


load_dotenv()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","all-MiniLM-L6-v2")

LLM_MODEL = os.getenv("LLM_MODEL","phi4-mini")

THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.5"))

TOP_K = int(os.getenv("RAG_TOP_K", "2"))


# Load once when the application starts.
embedding_model = SentenceTransformer(EMBEDDING_MODEL)


# --------------------------------------------------
# Database
# --------------------------------------------------

def get_db_connection():
    """
    Create and return a PostgreSQL connection.
    """

    # TODO:
    # Return psycopg2.connect(...) using environment variables.
    db_conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")

    )
    print("DB connected successful!")
    return db_conn

# --------------------------------------------------
# Embedding
# --------------------------------------------------

def embed_question(question):
    """
    Convert a question into a 384-dimensional Python list.
    """

    # TODO:
    # Validate that question is not empty.
    # Generate embedding.
    # Convert embedding to a list.
    if question is None or not question.strip():
        raise ValueError("Question cannot be empty.")
    
    question_embedding = embedding_model.encode(question).tolist()

    return question_embedding


# --------------------------------------------------
# Retrieval
# --------------------------------------------------

def retrieve_chunks(
    question_embedding,
    threshold=THRESHOLD,
    top_k=TOP_K,
):
    """
    Retrieve relevant chunks from PostgreSQL.

    Returns a list of dictionaries.
    """

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # TODO:
        # Execute pgvector search against document_chunks.
        # Apply threshold.
        # Order by distance.
        # Apply Top-K.
        # Fetch results.
    
        db_search_query = """
        SELECT id, document_id, text, embedding <=> %s::vector AS distance, metadata FROM document_chunks
        WHERE embedding <=> %s::vector <= %s 
        ORDER BY distance LIMIT %s;"""
        cursor.execute(db_search_query, (question_embedding, question_embedding, threshold, top_k))
        
        rows = cursor.fetchall()
        chunks = []

        for row in rows:
            (
                chunk_id,
                document_id,
                text,
                distance,
                metadata,
            ) = row

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "text": text,
                    "distance": float(distance),
                    "metadata": metadata,
                }
            )

        return chunks

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# Context construction
# --------------------------------------------------

def build_context(chunks):
    """
    Create a single context string from retrieved chunks.
    """

    # TODO:
    # For each chunk, include:
    # [Chunk ID <id>]
    # <text>
    #
    # Join the individual sections with blank lines.
    chunk_parts = []
    for row in chunks:
        chunk_parts.append(f"[Chunk ID {row['chunk_id']}]\n" f"{row['text']}")
    context = "\n\n".join(chunk_parts)
    return context

# --------------------------------------------------
# Generation
# --------------------------------------------------

def generate_answer(question, context):
    """
    Generate a grounded answer using Ollama.
    """

    # TODO:
    # Construct a grounded prompt.
    # Call ollama.chat().
    # Return only response["message"]["content"].
    prompt = f"""
    You are a grounded question-answering assistant.

    Answer the question using ONLY the information explicitly stated
    in the context.

    Rules:
    - If the context directly contains the answer, answer concisely.
    - Cite the supporting chunk ID after the answer.
    - Do not use outside knowledge.
    - Do not add facts that are not present in the context.
    - If the context does not contain enough information, respond exactly:
    "The retrieved evidence is not sufficient to answer the question."
    

    Context = {context}
    Question = {question}
    Answer: 
    """
    generated_response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        options={
            "temperature": 0,
            },
    )
    llm_answer = generated_response["message"]["content"]
    return llm_answer
  

# --------------------------------------------------
# Complete RAG flow
# --------------------------------------------------

def run_rag(question):
    """
    Run embedding, retrieval, context construction,
    and grounded generation.
    """

    # TODO:
    # 1. Validate/normalize question.
    # 2. Embed question.
    # 3. Retrieve chunks.
    # 4. If no chunks, return without calling Ollama.
    # 5. Build context.
    # 6. Generate answer.
    # 7. Return question, answer and sources.
    embedding = embed_question(question)
    retrieved_chunks = retrieve_chunks(question_embedding=embedding)
    if not retrieved_chunks:
        return {
        "question": question,
        "answer": ("There is not enough information in the retrieved documents to answer this question."),
        "sources": [],
        }
    context_builder = build_context(chunks=retrieved_chunks)
    answer_generation = generate_answer(question=question, context=context_builder)
    return {
    "question": question,
    "answer": answer_generation,
    "sources": retrieved_chunks
    }



# --------------------------------------------------
# Temporary CLI test
# --------------------------------------------------

if __name__ == "__main__":
    user_question = input(
        "Enter your question: "
    )

    result = run_rag(question=user_question)

    print("\nANSWER")
    print("-" * 70)
    print(result["answer"])

    print("\nSOURCES")
    print("-" * 70)

    for source in result["sources"]:
        print(
            f"Chunk ID: {source['chunk_id']}"
        )
        print(
            f"Distance: {source['distance']:.4f}"
        )
        print(f"Text: {source['text']}")
        print()


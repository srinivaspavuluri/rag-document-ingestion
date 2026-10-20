# RAG Document Ingestion

A local Retrieval-Augmented Generation (RAG) pipeline. It ingests text documents into PostgreSQL with pgvector, then answers questions using only the retrieved chunks and cites the chunk IDs it used.

## Stack

| Part | Tool |
|---|---|
| Vector storage and search | PostgreSQL + pgvector |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`, 384 dimensions) |
| Answer generation | Ollama (`phi4-mini`) |
| API | FastAPI |

## How it works

**Ingestion** (`ingest.py`)
1. Hash the document content (SHA-256).
2. Skip the document if the same `source` and hash already exist.
3. Split it into chunks and embed each chunk.
4. Insert the parent document, then its chunks, in **one transaction**. If any step fails, everything rolls back, so a document can never be left half-ingested.

Running the same document twice is safe: the second run returns `{"status": "skipped"}`.

**Question answering** (`rag_core.py`)
1. Embed the question.
2. Retrieve the top-K chunks by cosine distance (`<=>`), filtered by a distance threshold.
3. If nothing passes the threshold, return without calling the LLM.
4. Otherwise, build a context from the chunks and ask the LLM to answer using that context only.

## Project structure

```
schema.sql    # PostgreSQL + pgvector tables
ingest.py     # document hashing, duplicate check, chunking, transactional insert
rag_core.py   # DB connection, embedding, retrieval, context building, generation
main.py       # FastAPI app: GET /health, POST /ask
```

## Setup

**Requirements:** Python 3.10+, PostgreSQL with the pgvector extension installed, and Ollama running locally.

```bash
pip install -r requirements.txt
ollama pull phi4-mini
cp .env.example .env      # then fill in your DB credentials
```

### Database schema

Create the tables from [`schema.sql`](schema.sql):

```bash
psql -h localhost -U <DB_USER> -d <DB_NAME> -f schema.sql
```

- `documents`: one row per document, unique on `(source, content_hash)`, which is what makes re-ingestion skip duplicates.
- `document_chunks`: chunk text, a `vector(384)` embedding and JSONB metadata. Unique on `(document_id, chunk_index)`; deleting a document cascades to its chunks.

## Usage

**Ingest the sample document:**
```bash
python ingest.py
```
```
First run:  {'status': 'ingested', 'document_id': ..., 'chunks': 3}
Second run: {'status': 'skipped', 'document_id': None, 'chunks': 0}
```

**Ask a question from the CLI:**
```bash
python rag_core.py
```

**Run the API:**
```bash
uvicorn main:app --reload
```
```bash
curl -X POST http://127.0.0.1:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What does pgvector add to PostgreSQL?"}'
```
Interactive docs: http://127.0.0.1:8000/docs

## Status and next steps

- [x] Idempotent, transactional document ingestion
- [x] Threshold + top-K retrieval with grounded generation
- [x] FastAPI endpoint
- [ ] Replace the placeholder chunker (currently one paragraph = one chunk)
- [ ] Handle document updates and deletion
- [ ] Add a pgvector index (HNSW / IVFFlat) for performance

import hashlib
from rag_core import get_db_connection, embedding_model
import psycopg2


def content_hash(content: str) -> str:
    if not isinstance(content, str):
        raise TypeError("Document content must be a string.")

    if not content.strip():
        raise ValueError("Document content cannot be empty.")

    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def insert_doc(cursor, source:str, title: str, document_hash:str) -> int|None:
    if not source or not source.strip():
        raise ValueError("Source must not be empty.")

    insert_query = """
    INSERT INTO public.documents(source, title, content_hash) 
    VALUES (%s, %s, %s)
    ON CONFLICT (source, content_hash)
    DO NOTHING 
    RETURNING id;"""
    cursor.execute(insert_query, (source, title, document_hash))
    row = cursor.fetchone()

    if row is None:
        return None
    
    return row[0]

def insert_chunks(cursor, document_id, chunks, embeddings):
    if document_id is None:
        raise ValueError("document_id is required; duplicate documents must be skipped before chunk insertion.")
    if len(chunks) != len(embeddings):
        raise ValueError("Length does not match so value mismatch.")

    query = """
    INSERT INTO public.document_chunks(document_id, chunk_index, text, embedding)
    VALUES (%s, %s, %s, %s::vector)
    """
    zipped_data = zip(chunks, embeddings)
    for chunk_index, data in enumerate(zipped_data):
        chunk_content, embedding = data
        cursor.execute(query, (document_id, chunk_index, chunk_content, embedding.tolist()))

    return len(chunks)

def chunk_text(content: str) -> list[str]:
    # TEMPORARY placeholder: one paragraph = one chunk. Replaced later.
    return [p.strip() for p in content.split("\n\n") if p.strip()]


def document_exists(cursor, source: str, document_hash: str) -> bool:
    query = """
    SELECT id FROM public.documents WHERE source = %s AND content_hash = %s;"""
    cursor.execute(query, (source, document_hash))
    row = cursor.fetchone()
    return row is not None


def ingest_document(source: str, title: str, content: str) -> dict:
    document_hash = content_hash(content)
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if document_exists(cursor=cursor, source=source, document_hash=document_hash):
                return {"status": "skipped", "document_id": None, "chunks": 0}
            chunks = chunk_text(content)
            embeddings = embedding_model.encode(chunks)
            
            document_id = insert_doc(cursor=cursor, source=source, title=title, document_hash=document_hash)
            if document_id is None:
                connection.rollback()
                return {"status": "skipped", "document_id": None, "chunks": 0}

            inserted = insert_chunks(cursor=cursor, document_id=document_id, chunks=chunks, embeddings=embeddings)
            
            connection.commit()
        return {"status": "ingested", "document_id": document_id, "chunks": inserted}
    
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()






# Temporary Test Block
'''
if __name__ == "__main__":
    content_a = "Fast api is a plug and play api framework."
    content_b = "Fast api is a plug and play api framework."
    content_c = "Fast api is a plug and play api framework!"

    hash_a = content_hash(content_a)
    hash_b = content_hash(content_b)
    hash_c = content_hash(content_c)


    print("Hash-A: ", hash_a)
    print("Hash-B: ", hash_b)
    print("Hash-C: ", hash_c)

    print("Hash A equals Hash B: ", hash_a == hash_b)
    print("Hash A equals Hash C: ", hash_a == hash_c)
    print("Length: ", len(hash_a))

'''
# Temporary test for Insert document
'''
if __name__ == "__main__":

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Read the exact source and hash already stored.
            cursor.execute(
                """
                SELECT
                    source,
                    title,
                    content_hash
                FROM public.documents
                WHERE id = 1;
                """
            )

            existing_document = cursor.fetchone()

            if existing_document is None:
                raise RuntimeError("Document ID 1 was not found.")

            source, title, existing_hash = existing_document

            returned_id = insert_doc(
                cursor=cursor,
                source=source,
                title=title,
                content_hash=existing_hash
            )

            print("Returned document ID:", returned_id)

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM public.documents;
                """
            )

            document_count = cursor.fetchone()[0]
            print("Document count:", document_count)

        connection.rollback()

    finally:
        connection.close()
'''

# Temprary testing for the Insert document + Chunks
'''
if __name__ == "__main__":
    connection = get_db_connection()

    probe_source = "test_ingest_probe"
    probe_hash = content_hash("temporary ingestion probe content")

    try:
        with connection.cursor() as cursor:
            document_id = insert_doc(
                cursor=cursor,
                source=probe_source,
                title="Temporary Ingestion Probe",
                document_hash=probe_hash
            )
            print("Probe document ID:", document_id)

            chunks = ["probe chunk one", "probe chunk two", "probe chunk three"]
            embeddings = embedding_model.encode(chunks)

            insert_chunks(cursor, document_id, chunks, embeddings)
            print("First chunk call insert succeeded")

            cursor.execute(
                "SELECT COUNT(*) FROM public.document_chunks WHERE document_id = %s;",
                (document_id,)
            )
            print("Chunks visible inside transaction:", cursor.fetchone()[0])

            try:
                insert_chunks(cursor, document_id, chunks, embeddings)
                print("Second call unexpectedly SUCCEEDED")
            except psycopg2.errors.UniqueViolation:
                print("Second call raised UniqueViolation as expected")

            connection.rollback()

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM public.documents WHERE source = %s;",
                (probe_source,)
            )
            print("Probe documents after rollback:", cursor.fetchone()[0])

            cursor.execute(
                "SELECT COUNT(*) FROM public.document_chunks WHERE document_id = %s;",
                (document_id,)
            )
            print("Probe chunks after rollback:", cursor.fetchone()[0])

    finally:
        connection.close()

'''
if __name__ == "__main__":
    sample = """FastAPI is a modern Python web framework for building APIs.

It uses type hints for request validation and automatic documentation.

pgvector adds a vector column type and similarity operators to PostgreSQL."""

    print("First run: ", ingest_document("sample_fastapi.txt", "FastAPI Sample", sample))
    print("Second run:", ingest_document("sample_fastapi.txt", "FastAPI Sample", sample))
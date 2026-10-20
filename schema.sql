-- Schema for rag-document-ingestion
-- Generated from: pg_dump -s --no-owner --no-privileges (PostgreSQL 18.6), cleaned for readability.
-- Run: psql -h <host> -U <user> -d <db> -f schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Parent table: one row per ingested document version
CREATE TABLE public.documents (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL,
    title        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash TEXT NOT NULL,
    CONSTRAINT documents_source_hash_unique UNIQUE (source, content_hash)
);

-- Child table: chunks with their 384-dim embeddings (all-MiniLM-L6-v2)
CREATE TABLE public.document_chunks (
    id          BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    text        TEXT NOT NULL,
    embedding   public.vector(384) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    chunk_index INTEGER NOT NULL,
    CONSTRAINT document_chunks_position_unique UNIQUE (document_id, chunk_index),
    CONSTRAINT document_chunks_document_fk FOREIGN KEY (document_id)
        REFERENCES public.documents(id) ON DELETE CASCADE
);

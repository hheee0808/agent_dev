"""DB 스키마 + 연결 — pgvector document_chunks."""

from __future__ import annotations

import json
import logging
import os

import psycopg
from pgvector.psycopg import register_vector

from backend.ingest.embedding import EMBEDDING_DIM

log = logging.getLogger(__name__)


def get_conn_str() -> str:
    return (
        f"host={os.getenv('PG_HOST', 'localhost')} "
        f"port={os.getenv('PG_PORT', '5434')} "
        f"dbname={os.getenv('PG_DB', 'agent_dev')} "
        f"user={os.getenv('PG_USER', 'postgres')} "
        f"password={os.getenv('PG_PASSWORD', 'devpass')}"
    )


def get_connection():
    conn = psycopg.connect(get_conn_str())
    register_vector(conn)
    return conn


def ensure_schema() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_type TEXT,
                    file_size INT,
                    summary TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
                    source TEXT,
                    chunk_index INT,
                    content TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIM}),
                    page_number INT DEFAULT 1,
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON document_chunks USING hnsw (embedding vector_cosine_ops)
            """)
        conn.commit()
        log.info("schema ensured")
    finally:
        conn.close()

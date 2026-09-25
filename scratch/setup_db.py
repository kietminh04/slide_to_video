import psycopg2
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_URL = "postgresql://neondb_owner:npg_nxpTPCEFjG09@ep-icy-voice-b3ds7ltx-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

try:
    print("Connecting to Neon Database...")
    conn = psycopg2.connect(DB_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # 1. Enable pgvector
    print("Enabling pgvector extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create the document_chunks table
    print("Creating document_chunks table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id BIGSERIAL PRIMARY KEY,
            project_id VARCHAR(100),
            chapter_name VARCHAR(255),
            section_name VARCHAR(255),
            chunk_text TEXT,
            embedding VECTOR(1536),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Create HNSW index
    print("Creating HNSW index for vector search...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops);
    """)

    print("✅ Setup complete! Database is ready for RAG.")

    cur.close()
    conn.close()
except Exception as e:
    print("❌ Error:", e)

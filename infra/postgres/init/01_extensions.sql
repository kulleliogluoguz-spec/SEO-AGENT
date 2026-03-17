-- Enable pgvector extension for embedding/semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram search for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GoaConnect PostgreSQL Initialization
-- Requires: postgis, pgvector extensions

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Security schema (isolated from tourism data)
CREATE SCHEMA IF NOT EXISTS security;
CREATE SCHEMA IF NOT EXISTS tourism;
CREATE SCHEMA IF NOT EXISTS audit;

-- =========================================================================
-- Migration: admin-uploaded library documents, on top of the built-in set
-- in app/static/library/manifest.json (which this does not touch).
--
--   psql -U postgres -d whariki_connect -f migrate_library_documents.sql
--
-- Not needed if you are rebuilding the database from scratch -
-- create_database.sql already contains this.
-- =========================================================================

CREATE TABLE IF NOT EXISTS Library_Documents (
    document_id     SERIAL PRIMARY KEY,
    slug            VARCHAR(150) NOT NULL UNIQUE,
    title           VARCHAR(200) NOT NULL,
    description     VARCHAR(500),
    category        VARCHAR(50) NOT NULL,
    filename        VARCHAR(255) NOT NULL,
    size_mb         NUMERIC(6,2),
    uploaded_by     INT REFERENCES Users(user_id),
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

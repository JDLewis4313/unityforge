-- Basic database initialization script
-- This script will create the basic database structure
-- Actual schema will be created through migrations

-- Create user with password
-- Note: For security, in production use a more complex password
ALTER USER postgres WITH PASSWORD 'ChildofJesus#4313';

-- Set client encoding and timezone
ALTER ROLE postgres SET client_encoding TO 'utf8';
ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres SET timezone TO 'UTC';

-- Set up database if it doesn't exist (will be skipped if DB already exists)
CREATE DATABASE unityforge_dev WITH OWNER postgres ENCODING 'UTF8' LC_COLLATE 'en_US.utf8' LC_CTYPE 'en_US.utf8';

-- Connect to the database
\c unityforge_dev

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Note: Schema will be created using Flask-Migrate migrations
-- This file only sets up the database user and initial database
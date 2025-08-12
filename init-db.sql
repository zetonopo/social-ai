-- PostgreSQL initialization script
-- This script will be executed when the PostgreSQL container starts for the first time

-- Create the database if it doesn't exist (though POSTGRES_DB should handle this)
-- CREATE DATABASE IF NOT EXISTS social_ai_db;

-- Grant all privileges to the user (this is usually done automatically, but just to be sure)
GRANT ALL PRIVILEGES ON DATABASE social_ai_db TO social_ai_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES FOR USER social_ai_user IN SCHEMA public GRANT ALL ON TABLES TO social_ai_user;
ALTER DEFAULT PRIVILEGES FOR USER social_ai_user IN SCHEMA public GRANT ALL ON SEQUENCES TO social_ai_user;
ALTER DEFAULT PRIVILEGES FOR USER social_ai_user IN SCHEMA public GRANT ALL ON FUNCTIONS TO social_ai_user;

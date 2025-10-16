-- Prep script for local PostgreSQL
-- Usage:
--   sudo -u postgres PGPASSWORD='ADMIN_PASSWORD'  psql -v db_user='oob' -v db_name='oob01' -v db_pass='SECRET' -f install/prep.sql

-- Create role
SELECT format('CREATE ROLE %I WITH LOGIN PASSWORD %L', :'db_user', :'db_pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_user')
\gexec

-- Create database
SELECT format('CREATE DATABASE %I OWNER %I TEMPLATE template0 ENCODING ''UTF8''', :'db_name', :'db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name')
\gexec

-- Ensure schema 'public' exists
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'public') THEN
    EXECUTE 'CREATE SCHEMA public';
  END IF;
END $$;

-- Grants for app user
GRANT CONNECT, TEMP ON DATABASE :"db_name" TO :"db_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"db_user";
GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA public TO :"db_user";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO :"db_user";

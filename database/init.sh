#!/bin/sh
set -eu
app_password="$(cat /run/secrets/db_app_password)"
migration_password="$(cat /run/secrets/db_migration_password)"
# Provisioner generates only URL-safe secrets; reject anything unsafe for SQL literals.
case "$app_password$migration_password" in *[!a-zA-Z0-9_-]*) exit 1 ;; esac
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<SQL
CREATE ROLE planner_app LOGIN PASSWORD '$app_password';
CREATE ROLE planner_migrate LOGIN PASSWORD '$migration_password';
ALTER DATABASE planner OWNER TO planner_migrate;
ALTER SCHEMA public OWNER TO planner_migrate;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO planner_app;
ALTER DEFAULT PRIVILEGES FOR ROLE planner_migrate IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO planner_app;
SQL

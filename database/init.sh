#!/bin/bash
# TradeEasy Database Initialization Script
# Executes all database migration scripts in order

set -e

echo "Running TradeEasy database initialization scripts..."

# Check if PGPASSWORD environment variable is set
if [ -z "$PGPASSWORD" ]; then
    echo "Warning: PGPASSWORD environment variable not set."
    echo "Using default credentials from docker-compose."
    export PGPASSWORD="tradeeasy"
fi

# Default PostgreSQL connection parameters
PG_HOST=${PG_HOST:-"localhost"}
PG_PORT=${PG_PORT:-"5432"}
PG_USER=${PG_USER:-"tradeeasy"}
PG_DB=${PG_DB:-"tradeeasy"}

# Function to execute SQL scripts
function execute_sql_script {
    local script=$1
    echo "Executing script: $script"
    psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB -f "$script"
}

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create database if it doesn't exist
echo "Ensuring database exists..."
psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$PG_DB'" | grep -q 1 || psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d postgres -c "CREATE DATABASE $PG_DB"

# Execute initialization scripts in order
echo "Creating tables..."
execute_sql_script "$DIR/migrations/init/01_create_tables.sql"

echo "Creating indexes..."
execute_sql_script "$DIR/migrations/init/02_create_indexes.sql"

echo "Inserting seed data..."
execute_sql_script "$DIR/migrations/init/03_seed_data.sql"

echo "Database initialization completed successfully!"

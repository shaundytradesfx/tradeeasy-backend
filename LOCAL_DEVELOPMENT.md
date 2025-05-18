# Local Development Guide for TradeEasy Backend

This guide explains how to set up and run the TradeEasy backend application locally for development purposes.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10.0 or higher)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0.0 or higher)
- Git

## Quick Start

The easiest way to run the application locally is using the provided `docker-compose.local.yml` file:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/shaundytradesfx/tradeeasy-backend.git
cd tradeeasy-backend

# Build and start all services in detached mode
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f web
```

This will start:
- The FastAPI application on http://localhost:8000
- PostgreSQL database on port 5432
- PgAdmin web interface on http://localhost:5050
- A test database on port 5433 (for running tests)

## Services Overview

### 1. Web Application (FastAPI)

The main FastAPI application is accessible at http://localhost:8000 with documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

The application code is mounted from your local directory, so changes will trigger a reload of the server automatically.

### 2. PostgreSQL Database

The main database runs on port 5432 with the following credentials:
- Host: localhost (or `db` from within Docker network)
- Port: 5432
- Database: tradeeasy
- Username: tradeeasy
- Password: tradeeasy

### 3. PgAdmin

PgAdmin is a web-based administration tool for PostgreSQL. Access it at http://localhost:5050 with:
- Email: admin@tradeeasy.com
- Password: admin

After logging in, you need to add a new server connection:
1. Right-click on "Servers" in the left panel and select "Create > Server"
2. Name: TradeEasy
3. In the "Connection" tab:
   - Host: db
   - Port: 5432
   - Database: tradeeasy
   - Username: tradeeasy
   - Password: tradeeasy

### 4. Test Database

A separate PostgreSQL instance is available for testing on port 5433. This is useful for running tests that require a database without affecting your development data.

## Development Workflow

1. **Run the application**:
   ```bash
   docker-compose -f docker-compose.local.yml up
   ```

2. **Make changes to the code**:
   Edit files in your IDE. The application will automatically reload when you save changes.

3. **Run tests**:
   ```bash
   # Use the test-db for tests
   docker-compose -f docker-compose.local.yml exec web pytest
   ```

4. **Access health check**:
   Open http://localhost:8000/health in your browser or use:
   ```bash
   curl http://localhost:8000/health
   ```

5. **Stop the application**:
   ```bash
   docker-compose -f docker-compose.local.yml down
   ```

6. **Reset everything (including data volumes)**:
   ```bash
   docker-compose -f docker-compose.local.yml down -v
   ```

## Troubleshooting

### Database Connection Issues

If the web application can't connect to the database:
1. Check if the database container is running: `docker-compose -f docker-compose.local.yml ps`
2. Verify the database logs: `docker-compose -f docker-compose.local.yml logs db`
3. Ensure the DATABASE_URL is correctly set in the web service environment

### Application Not Reloading

If code changes aren't reflected:
1. Check that the volumes are mounted correctly
2. Verify the application logs: `docker-compose -f docker-compose.local.yml logs web`
3. Restart the web service: `docker-compose -f docker-compose.local.yml restart web`

### PgAdmin Issues

If you can't connect to the database from PgAdmin:
1. Make sure you're using `db` (not localhost) as the hostname within PgAdmin
2. Check that both services are on the same Docker network

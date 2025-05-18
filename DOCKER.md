# Docker Guide for TradeEasy Backend

This document provides instructions for running and deploying the TradeEasy backend using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your system
- [Docker Compose](https://docs.docker.com/compose/install/) for running multi-container applications

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose, which sets up both the FastAPI application and the PostgreSQL database:

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The application will be available at http://localhost:8000

## Building the Docker Image Manually

If you want to build the Docker image manually:

```bash
# Build the image
docker build -t tradeeasy-backend .

# Run the container (requires a PostgreSQL database)
docker run -d -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host:5432/tradeeasy \
  -e RSS_SOURCES=https://example.com/rss/feed \
  -e SECRET_KEY=yoursecretkey \
  --name tradeeasy tradeeasy-backend
```

## Docker Configuration Files

- `Dockerfile`: Multi-stage build for optimized production image
- `docker-compose.yml`: Service definitions for the application and database
- `.dockerignore`: Files excluded from the Docker build context

## Environment Variables

The application is configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | Connection string for PostgreSQL | postgresql://tradeeasy:tradeeasy@db:5432/tradeeasy |
| RSS_SOURCES | Comma-separated list of RSS feed URLs | (See docker-compose.yml) |
| LOG_LEVEL | Logging level | INFO |
| SECRET_KEY | Secret key for securing the application | (Required in production) |

## Development with Docker

For development, you can use the volume mount in the docker-compose.yml to have live-reloading of your code:

```bash
# Start the development environment
docker-compose up
```

Any changes you make to the code in the `app` directory will be reflected immediately.

## Production Deployment Considerations

For production deployment:

1. Use a unique, strong SECRET_KEY
2. Consider using Docker secrets for sensitive information
3. Configure the database with strong credentials
4. Set up proper backups for the database volume
5. Consider using a container orchestration system like Kubernetes
6. Set up proper monitoring and alerting

## Health Checks

The application includes a health check endpoint at `/health` which is also configured in the Docker setup for automated monitoring.

## Troubleshooting

If you encounter issues:

1. Check the logs: `docker-compose logs` or `docker logs tradeeasy`
2. Verify the database connection
3. Ensure the required environment variables are set correctly
4. Check the container status: `docker ps -a`

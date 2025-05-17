# GitHub Actions CI/CD for TradeEasy Backend

This document explains the GitHub Actions workflows set up for the TradeEasy backend project.

## Workflows Overview

We have set up several workflows to ensure code quality, test coverage, and deployment automation:

1. **CI/CD Pipeline** (`main.yml`): A comprehensive workflow that runs linting, testing, and Docker image building sequentially.
2. **Linting** (`lint.yml`): Checks code quality using flake8, black, isort, and mypy.
3. **Testing** (`test.yml`): Runs pytest with PostgreSQL service for integration testing.
4. **Docker Build** (`build.yml`): Builds and tests the Docker image.
5. **Deployment** (`deploy.yml`): Handles deployment to production when code is pushed to the main branch or tagged with a version.

## Triggering Workflows

- All workflows run on push to `main` and `develop` branches
- All workflows run on pull requests targeting `main` and `develop` branches
- Deployment workflow additionally runs when tags matching `v*` are pushed (e.g., v1.0.0)

## Required Secrets

For the workflows to function properly, you need to set up the following secrets in your GitHub repository:

- `DOCKER_HUB_USERNAME`: Your Docker Hub username
- `DOCKER_HUB_TOKEN`: Your Docker Hub access token

To add these secrets:
1. Go to your GitHub repository
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret" and add each secret

## Development Workflow

Our recommended development workflow is:

1. Create a feature branch from `develop`
2. Make your changes and commit them
3. Push your branch and create a pull request to `develop`
4. GitHub Actions will automatically run the linting, testing, and build workflows
5. Once the PR is approved and all checks pass, merge to `develop`
6. For releases, merge `develop` to `main` or create a tag

## Adding Custom Checks

To add additional checks to the workflows:

1. Edit the appropriate workflow file in `.github/workflows/`
2. Add new steps to the job
3. Commit and push your changes

## Troubleshooting

If a workflow fails, you can:

1. Click on the failing workflow in the GitHub Actions tab
2. Examine the logs to identify the issue
3. Fix the issue in your code
4. Push a new commit to trigger the workflow again

## Local Testing

Before pushing changes, you can run the same checks locally:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 .
black --check app tests
isort --check --profile black app tests
mypy app

# Run tests
pytest --cov=app

# Build and test Docker image
docker build -t tradeeasy-backend:test .
docker run -d --name tradeeasy-test -e DATABASE_URL=sqlite:///tradeeasy.db -e TESTING=true tradeeasy-backend:test
``` 
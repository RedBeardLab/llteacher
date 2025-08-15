# LLTeacher v2

AI-assisted educational platform for teachers and students.

## Project Structure

This project uses [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) for dependency management.

### Workspace Members

- **`apps/accounts`** - User management and authentication
- **`apps/conversations`** - AI conversation handling and submissions
- **`apps/homeworks`** - Homework and section management
- **`apps/llm`** - LLM configuration and services
- **`core`** - Shared utilities and base classes
- **`permissions`** - Permission decorators and utilities
- **`services`** - Business logic service layer
- **`src/llteacher`** - Main Django project

## Setup

1. Install uv: `pip install uv`
2. Install dependencies: `uv sync`
3. Run migrations: `python manage.py migrate`
4. Create superuser: `python manage.py createsuperuser`
5. Run development server: `python manage.py runserver`

## Development

- Each app is a separate workspace member with its own `pyproject.toml`
- Use `uv add <package>` to add dependencies to specific workspaces
- Use `uv sync` to install all workspace dependencies

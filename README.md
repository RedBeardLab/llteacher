# LLTeacher v2

AI-assisted educational platform for teachers and students.

## 🚀 Project Status

**Phase 1 Complete**: Data Models & Testing Infrastructure ✅

- ✅ **Models**: All Django models implemented according to design specifications
- ✅ **Testing**: 149 comprehensive test cases with 350x performance optimization
- ✅ **Architecture**: Clean, modular structure with proper separation of concerns
- ✅ **Documentation**: Comprehensive testing guide and setup instructions

**Next Phase**: Service Layer & API Development 🔄

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

## Testing

The project includes comprehensive testing with **149 test cases** covering all models and their functionality.

### Quick Start

```bash
# Run all tests (fastest - uses in-memory database)
uv run python run_tests.py

# Run with verbose output
uv run python run_tests.py --verbosity=2

# Run specific app tests
uv run python run_tests.py apps.accounts.tests
```

### Performance

- **Standard Django tests**: ~21.348 seconds
- **Optimized tests**: ~0.061 seconds
- **Speed improvement**: **350x faster!** 🚀

### Test Coverage

- ✅ **Models**: Complete coverage of all Django models
- ✅ **Relationships**: Foreign keys, one-to-one, cascade deletes
- ✅ **Validation**: Custom validation methods and business logic
- ✅ **Edge Cases**: Special characters, long content, boundaries
- ✅ **Properties**: Custom properties and computed fields

For detailed testing information, see [TESTING.md](TESTING.md).

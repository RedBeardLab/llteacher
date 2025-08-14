# Technical Architecture

## Technology Stack

### Backend Framework
- **Django 5.2.4**: Modern Python web framework with built-in admin interface
- **Python 3.12+**: Latest Python version for performance and modern features

### Package Management
- **uv**: Fast Python package installer and resolver
- **Monorepo Structure**: Single repository with multiple packages for better dependency management

### Database
- **SQLite**: File-based database for development and simple deployments
- **Django ORM**: Object-relational mapping with automatic migrations

### Frontend
- **Bootstrap 5**: Modern CSS framework for responsive design
- **Crispy Forms**: Django forms rendering with Bootstrap styling
- **Flatpickr**: Date/time picker for better user experience

### Deployment
- **Gunicorn**: WSGI HTTP server for production
- **WhiteNoise**: Static file serving for Django applications

## Project Structure

```
llteacher/
├── apps/                          # Application packages
│   ├── accounts/                  # User management and authentication
│   ├── homeworks/                 # Homework assignment management
│   └── llm_interactions/          # LLM conversation handling
├── llteacher/                     # Main Django project
│   ├── settings.py               # Django configuration
│   ├── urls.py                   # Main URL routing
│   └── wsgi.py                   # WSGI application entry point
├── templates/                     # HTML templates
├── static/                        # Static files (CSS, JS, images)
├── manage.py                      # Django management script
├── pyproject.toml                 # Project configuration and dependencies
└── uv.lock                       # Locked dependency versions
```

## Application Architecture

### 1. Accounts App (`apps/accounts/`)

**Purpose**: User authentication, role management, and user profiles

**Key Components**:
- Custom User model extending Django's AbstractUser
- Teacher and Student profile models
- Role determination utilities

**Architecture Decisions**:
- Uses Django's built-in authentication system
- Separate profile models for different user types
- Helper functions for role checking

### 2. Homeworks App (`apps/homeworks/`)

**Purpose**: Homework assignment creation, management, and submission tracking

**Key Components**:
- Homework model for assignments
- Solution model for teacher reference solutions
- StudentSubmission for tracking student work
- TeacherTestSubmission for testing assignments

**Architecture Decisions**:
- Separate models for homework and solutions
- Status tracking for submissions
- Due date management

### 3. LLM Interactions App (`apps/llm_interactions/`)

**Purpose**: Managing conversations between users and AI tutors

**Key Components**:
- Conversation model for chat sessions
- Message model for individual messages
- RCodeExecution for code execution tracking
- LLMConfig for AI service configuration

**Architecture Decisions**:
- Flexible conversation system supporting multiple submission types
- Message threading and ordering
- Configurable LLM parameters

## URL Routing Structure

### Main URLs (`llteacher/urls.py`)
```
/                           # Home page (redirects based on user type)
/welcome/                   # Public landing page
/health/                    # Health check endpoint
/admin/                     # Django admin interface
/accounts/                  # Authentication URLs
/homeworks/                 # Homework management
/llm/                       # LLM interaction endpoints
```

### Homework URLs (`apps/homeworks/urls.py`)
```
/homeworks/                 # List homeworks (role-based view)
/homeworks/create/          # Create new homework (teachers only)
/homeworks/<id>/            # Homework detail view
/homeworks/<id>/edit/       # Edit homework (teachers only)
/homeworks/<id>/delete/     # Delete homework (teachers only)
/submission/create/         # Create student submission
```

### LLM Interaction URLs (`apps/llm_interactions/urls.py`)
```
/llm/conversation/<id>/     # View conversation
/llm/start/<submission_id>/ # Start new conversation
/llm/send_message/          # Send message to LLM
/llm/execute_code/          # Execute R code
```

## Database Design

### Key Relationships

1. **User → Teacher/Student**: One-to-one relationships for role-specific profiles
2. **Teacher → Homework**: One-to-many (teachers create multiple homeworks)
3. **Homework → Solution**: One-to-one (each homework has one reference solution)
4. **Homework → StudentSubmission**: One-to-many (multiple students can submit)
5. **StudentSubmission → Conversation**: One-to-one (each submission has one conversation)
6. **Conversation → Message**: One-to-many (conversations contain multiple messages)

### Database Constraints

- Foreign key relationships with CASCADE deletion
- Unique constraints on one-to-one relationships
- Custom validation in Conversation model for submission type exclusivity

## Security Architecture

### Authentication
- Django's built-in session-based authentication
- Login required decorators on all views
- Role-based access control through profile checking

### Authorization
- View-level permission checking
- Resource ownership validation
- Teacher-only access to certain operations

### Data Protection
- CSRF protection enabled
- SQL injection protection through Django ORM
- Input validation and sanitization

## Performance Considerations

### Database Optimization
- Select-related and prefetch-related for reducing queries
- Proper indexing on foreign keys
- Efficient query patterns in views

### Caching Strategy
- No explicit caching layer implemented
- Django's built-in caching available but not utilized
- Static file serving through WhiteNoise

### Scalability
- Monorepo structure allows for easy scaling
- Modular app design supports horizontal scaling
- Database can be easily migrated to PostgreSQL/MySQL

## Deployment Architecture

### Development Environment
- SQLite database for simplicity
- Django development server
- Local file storage

### Production Considerations
- Gunicorn WSGI server
- WhiteNoise for static file serving
- Environment variable configuration
- Health check endpoints for monitoring

## Integration Points

### LLM Services
- Configurable API endpoints
- Support for multiple providers (OpenAI, Claude, etc.)
- Environment variable-based API key management

### External Dependencies
- OpenAI Python client for GPT models
- R language integration for code execution
- Bootstrap and CSS frameworks for UI

## Monitoring and Observability

### Health Checks
- Database connectivity monitoring
- Cache availability checking
- HTTP status endpoint for load balancers

### Logging
- Django's built-in logging system
- No custom logging implementation
- Error tracking through Django's error handling

## Configuration Management

### Environment Variables
- Django secret key
- Database configuration
- LLM API keys and endpoints
- Debug settings

### Settings Structure
- Base settings in `settings.py`
- Production overrides in `production.py`
- Environment-specific configurations

## Testing Strategy

### Test Coverage
- Unit tests for models and forms
- View tests for business logic
- Integration tests for workflows

### Test Data
- Factory patterns for test data creation
- Management commands for test user creation
- Isolated test database

## Known Issues and Limitations

### 1. **Model Complexity**
- Overly complex conversation model with nullable foreign keys
- Redundant submission models
- Inconsistent data types

### 2. **Performance**
- No caching strategy
- Potential N+1 query problems
- Large text fields without size limits

### 3. **Scalability**
- SQLite limitations for production
- No horizontal scaling strategy
- Single-server architecture

### 4. **Maintainability**
- Complex permission logic in views
- Business logic mixed with presentation
- Tight coupling between models

## Future Architecture Considerations

### 1. **Microservices**
- Separate services for different domains
- API-first design
- Event-driven architecture

### 2. **Modern Frontend**
- React/Vue.js frontend
- RESTful API backend
- Real-time communication

### 3. **Cloud Native**
- Container-based deployment
- Kubernetes orchestration
- Cloud database services

### 4. **Event Sourcing**
- Audit trail for all changes
- Temporal data modeling
- CQRS pattern implementation

## Conclusion

The current architecture demonstrates a solid foundation with Django best practices but suffers from:

1. **Over-engineering** in the data model
2. **Tight coupling** between components
3. **Performance limitations** due to missing optimizations
4. **Scalability constraints** from architectural decisions

The redesign should focus on:
- **Simplified data model** with clear relationships
- **Service layer** for business logic
- **API-first design** for future frontend flexibility
- **Event-driven architecture** for better scalability
- **Modern deployment** patterns for cloud environments

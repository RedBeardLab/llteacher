# LLTeacher v2 - System Design Document

## Executive Summary

LLTeacher v2 is a redesigned version of the AI-assisted educational platform that addresses the critical architectural flaws of v1 while maintaining the core innovative concept. The system allows teachers to create homework assignments with multiple sections, each with optional solutions, and students to interact with AI tutors to work through these sections individually.

## Core Changes from v1

### 1. **Data Model Restructuring**
- **UUID Primary Keys**: All models now use UUIDs instead of integers
- **Sectioned Homework**: Homework is split into 1-20 sections, each with optional solutions
- **Simplified Submission Model**: Submission tracks the selected conversation, which in turn tracks the assignment
- **Removed Grading**: No teacher feedback or grades stored in the system
- **Streamlined Models**: Removed unnecessary fields like bio, progress_notes, and soft delete complexity

### 2. **Improved Architecture**
- **Service Layer**: Business logic extracted from views into dedicated service classes
- **Centralized Permissions**: Unified permission system with decorators
- **Better Data Integrity**: Cleaner relationships and constraints
- **Performance Optimizations**: Proper database queries and caching strategy

### 3. **Enhanced User Experience**
- **Streamlined Workflows**: Reduced redirects and state changes
- **Progress Tracking**: Section completion and submission status
- **Flexible Navigation**: Students can work on sections in any order
- **Teacher Testing**: Teachers can test their homework assignments with the AI tutor

## System Architecture

### Technology Stack
- **Backend**: Django 5.2.4+ with Python 3.12+
- **Database**: SQLite (development and production)
- **Package Management**: uv for dependency management
- **Frontend**: Django templates with Bootstrap 5
- **LLM Integration**: OpenAI/Claude API with configurable parameters


### Project Structure
```
2_llteacher/
├── apps/                   # Django applications
│   ├── accounts/           # User management and authentication
│   ├── homeworks/          # Homework and section management
│   ├── conversations/      # AI conversation handling and submissions
│   └── llm/                # LLM configuration and services
├── core/                   # Shared utilities and base classes
├── services/               # Business logic service layer
├── permissions/            # Permission decorators and utilities
├── llteacher/              # Main Django project configuration
├── templates/              # Django templates
├── static/                 # Static files (CSS, JS, images)
├── manage.py               # Django management script
└── pyproject.toml          # Root project configuration
```

We are using uv workspaces to manage everything.

@https://docs.astral.sh/uv/concepts/projects/workspaces/

Each app will be in a separate workspace along with core, services, and permissions.

Each app (including the main application `llteacher`) need to be structured with a `src` directory and inside the `src` directory another directory with the name of the python module.



## Data Model Design

### Simplified Data Flow

The new model follows a clean, hierarchical structure:
- **Homework** contains multiple **Sections**
- **Sections** can have optional **Solutions** and multiple **Conversations**
- **Students** create **Conversations** with sections
- **Submissions** track which conversation represents the final work (section is derived from conversation)

This eliminates the complex nullable foreign key relationships from v1 and creates a clear, maintainable data structure.

### 1. User Management (`accounts` app)

```python
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom user model with UUID primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        db_table = 'accounts_user'

class Teacher(models.Model):
    """Teacher profile with one-to-one relationship to User."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_teacher'

class Student(models.Model):
    """Student profile with one-to-one relationship to User."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_student'
```

### 2. Homework Management (`homeworks` app)

```python
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Homework(models.Model):
    """Homework assignment with multiple sections."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey('accounts.Teacher', on_delete=models.CASCADE, related_name='homeworks_created')
    due_date = models.DateTimeField()
    llm_config = models.ForeignKey('llm.LLMConfig', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'homeworks_homework'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def section_count(self):
        return self.sections.count()
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return timezone.now() > self.due_date

class Section(models.Model):
    """Individual section within a homework assignment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    solution = models.OneToOneField('SectionSolution', on_delete=models.SET_NULL, null=True, blank=True, related_name='section')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'homeworks_section'
        ordering = ['order']
        unique_together = ['homework', 'order']
    
    def __str__(self):
        return f"{self.homework.title} - Section {self.order}: {self.title}"
    
class SectionSolution(models.Model):
    """Teacher-provided solution for a section."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'homeworks_section_solution'
    
    def __str__(self):
        return f"Solution for {self.section}"
```

### 3. Conversation Management (`conversations` app)

**Flexible Message Types**: The Message model supports any string value for message types, allowing for extensible conversation handling. Common types include:
- `student`: Regular student text messages
- `ai`: AI tutor responses
- `r_code`: R code submitted by students
- `code_execution`: Results of code execution
- `file_upload`: File attachments
- `system`: System notifications or status updates

```python
import uuid
from django.db import models
from django.core.validators import MinLengthValidator

class Conversation(models.Model):
    """AI conversation between user and LLM for a specific section."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='conversations')
    section = models.ForeignKey('homeworks.Section', on_delete=models.CASCADE, related_name='conversations')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations_conversation'
        ordering = ['-created_at']
    
    def __str__(self):
        user_type = "Teacher" if self.is_teacher_test else "Student"
        return f"{user_type} conversation {self.id} - {self.user.username} on {self.section}"
    
    def soft_delete(self):
        """Soft delete the conversation."""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def is_teacher_test(self):
        """Check if this is a teacher test conversation."""
        return hasattr(self.user, 'teacher_profile')
    
    @property
    def is_student_conversation(self):
        """Check if this is a student conversation."""
        return hasattr(self.user, 'student_profile')

class Message(models.Model):
    """Individual message in a conversation."""
    
    # Common message types (for reference, but not enforced)
    MESSAGE_TYPE_STUDENT = 'student'
    MESSAGE_TYPE_AI = 'ai'
    MESSAGE_TYPE_R_CODE = 'code'
    MESSAGE_TYPE_FILE_UPLOAD = 'file_upload'
    MESSAGE_TYPE_CODE_EXECUTION = 'code_execution'
    MESSAGE_TYPE_SYSTEM = 'system'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField(validators=[MinLengthValidator(1)])
    message_type = models.CharField(max_length=50, help_text="Type of message (e.g., 'student', 'ai', 'r_code', 'file_upload', etc.)")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversations_message'
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.message_type} message at {self.timestamp}"
    
    @property
    def is_from_student(self):
        """Check if this is a student message."""
        return self.message_type in [self.MESSAGE_TYPE_STUDENT, self.MESSAGE_TYPE_R_CODE, 
                                   self.MESSAGE_TYPE_FILE_UPLOAD, self.MESSAGE_TYPE_CODE_EXECUTION]
    
    @property
    def is_from_ai(self):
        """Check if this is an AI response."""
        return self.message_type == self.MESSAGE_TYPE_AI
    
    @property
    def is_system_message(self):
        """Check if this is a system message."""
        return self.message_type == self.MESSAGE_TYPE_SYSTEM

class Submission(models.Model):
    """Student submission for a specific section."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='submission')
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conversations_submission'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Submission by {self.conversation.user.username} for {self.conversation.section}"
    
    @property
    def section(self):
        """Get the section through the conversation."""
        return self.conversation.section
    
    @property
    def student(self):
        """Get the student through the conversation."""
        return self.conversation.user.student_profile
    
    def clean(self):
        """Ensure only one submission per student per section."""
        from django.core.exceptions import ValidationError
        
        # Check if another submission exists for the same student and section
        existing_submission = Submission.objects.filter(
            conversation__user=self.conversation.user,
            conversation__section=self.conversation.section
        ).exclude(id=self.id)
        
        if existing_submission.exists():
            raise ValidationError("Student already has a submission for this section.")
```

### 4. LLM Configuration (`llm` app)

**Simplified Configuration**: The LLMConfig model focuses on essential parameters without provider complexity. This assumes you're using a single, reliable LLM service (like OpenAI) and allows teachers to configure model behavior and prompts for their specific homework needs.

```python
import uuid
from django.db import models

class LLMConfig(models.Model):
    """Configuration for LLM integration."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    model_name = models.CharField(max_length=100, help_text="LLM model to use (e.g., 'gpt-4', 'gpt-3.5-turbo')")
    api_key_variable = models.CharField(max_length=100, help_text="Environment variable name for API key")
    base_prompt = models.TextField(help_text="Base prompt template for AI tutor")
    temperature = models.FloatField(default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)])
    max_tokens = models.PositiveIntegerField(default=1000)
    is_default = models.BooleanField(default=False, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'llm_config'
    
    def __str__(self):
        return f"{self.name} ({self.model_name})"
    
    def save(self, *args, **kwargs):
        """Ensure only one default config exists."""
        if self.is_default:
            LLMConfig.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
```

## Service Layer Design

### 1. Homework Service

```python
from django.db import transaction
from django.utils import timezone
from .models import Homework, Section, SectionSolution

class HomeworkService:
    """Service class for homework-related business logic."""
    
    @staticmethod
    def create_homework_with_sections(data, teacher):
        """Create homework with multiple sections."""
        with transaction.atomic():
            # Create homework
            homework = Homework.objects.create(
                title=data['title'],
                description=data['description'],
                due_date=data['due_date'],
                created_by=teacher,
                llm_config=data.get('llm_config')
            )
            
            # Create sections
            sections = []
            for section_data in data['sections']:
                section = Section.objects.create(
                    homework=homework,
                    title=section_data['title'],
                    content=section_data['content'],
                    order=section_data['order']
                )
                
                # Create solution if provided
                if section_data.get('solution'):
                    solution = SectionSolution.objects.create(
                        content=section_data['solution']
                    )
                    section.solution = solution
                    section.save()
                
                sections.append(section)
            
            return homework, sections
    
    @staticmethod
    def get_student_homework_progress(student, homework):
        """Get student's progress on a specific homework."""
        sections = homework.sections.order_by('order')
        progress = []
        
        for section in sections:
            try:
                submission = Submission.objects.filter(
                    conversation__user=student.user,
                    conversation__section=section
                ).first()
                if submission:
                    status = 'submitted'
                    conversation = submission.conversation
                else:
                    # Check if due date has passed for auto-submission
                    if homework.is_overdue:
                        status = 'overdue'
                        conversation = None
                    else:
                        status = 'not_started'
                        conversation = None
            except Exception:
                status = 'not_started'
                conversation = None
            
            progress.append({
                'section': section,
                'status': status,
                'conversation': conversation
            })
        
        return progress
```

### 2. Conversation Service

```python
from django.db import transaction
from .models import Conversation, Message
from llm.services import LLMService

class ConversationService:
    """Service class for conversation-related business logic."""
    
    @staticmethod
    def start_conversation(user, section):
        """Start a new conversation for a user on a section."""
        conversation = Conversation.objects.create(
            user=user,
            section=section
        )
        
        # Send initial AI message
        initial_message = ConversationService._create_initial_message(section)
        Message.objects.create(
            conversation=conversation,
            content=initial_message,
            message_type=Message.MESSAGE_TYPE_AI
        )
        
        return conversation
    
    @staticmethod
    def send_message(conversation, content, message_type='student'):
        """Send a user message and get AI response."""
        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            content=content,
            message_type=message_type
        )
        
        # Get AI response
        ai_response = LLMService.get_response(conversation, content, message_type)
        
        # Save AI response
        ai_message = Message.objects.create(
            conversation=conversation,
            content=ai_response,
            message_type=Message.MESSAGE_TYPE_AI
        )
        
        return ai_message
    

    
    @staticmethod
    def add_system_message(conversation, content):
        """Add a system message to the conversation."""
        return Message.objects.create(
            conversation=conversation,
            content=content,
            message_type=Message.MESSAGE_TYPE_SYSTEM
        )
    
    @staticmethod
    def delete_teacher_test_conversation(conversation):
        """Delete a teacher test conversation."""
        if not conversation.is_teacher_test:
            raise ValueError("Can only delete teacher test conversations.")
        
        conversation.soft_delete()
        return conversation
    
    @staticmethod
    def get_teacher_test_conversations(teacher, section=None):
        """Get teacher test conversations for a teacher."""
        queryset = teacher.user.conversations.filter(
            is_deleted=False
        )
        
        if section:
            queryset = queryset.filter(section=section)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def handle_r_code_execution(conversation, code, output, error=None):
        """Handle R code execution and add results to conversation."""
        # Add the R code as a student message
        code_message = Message.objects.create(
            conversation=conversation,
            content=code,
            message_type=Message.MESSAGE_TYPE_R_CODE
        )
        
        # Add the execution result
        if error:
            result_content = f"Error: {error}"
            result_type = Message.MESSAGE_TYPE_SYSTEM
        else:
            result_content = f"Output:\n{output}"
            result_type = Message.MESSAGE_TYPE_CODE_EXECUTION
        
        result_message = Message.objects.create(
            conversation=conversation,
            content=result_content,
            message_type=result_type
        )
        
        return code_message, result_message
    
    @staticmethod
    def _create_initial_message(section):
        """Create initial AI message for a section."""
        return f"Hello! I'm here to help you with Section {section.order}: {section.title}. What would you like to work on?"
```

### 3. Submission Service

```python
from django.db import transaction
from django.utils import timezone
from conversations.models import Submission
from homeworks.models import Section

class SubmissionService:
    """Service class for submission-related business logic."""
    
    @staticmethod
    def submit_section(user, conversation):
        """Submit a section with the selected conversation."""
        with transaction.atomic():
            # Check if submission already exists for this user and section
            existing_submission = Submission.objects.filter(
                conversation__user=user,
                conversation__section=conversation.section
            ).first()
            
            if existing_submission:
                # Update existing submission with new conversation
                existing_submission.conversation = conversation
                existing_submission.save()
                return existing_submission
            else:
                # Create new submission
                return Submission.objects.create(
                    conversation=conversation
                )
    
    @staticmethod
    def auto_submit_overdue_sections():
        """Automatically submit overdue sections for all students."""
        overdue_sections = Section.objects.filter(
            homework__due_date__lt=timezone.now()
        ).select_related('homework')
        
        for section in overdue_sections:
            # Find students without submissions for this section
            students_without_submissions = section.homework.students.exclude(
                submissions__conversation__section=section
            )
            
            for student in students_without_submissions:
                # Find their most recent conversation for this section
                try:
                    conversation = section.conversations.filter(
                        user=student.user
                    ).latest('created_at')
                    
                    # Auto-submit
                    SubmissionService.submit_section(student.user, conversation)
                except Conversation.DoesNotExist:
                    # No conversation exists, skip
                    pass
```

## Permission System

### 1. Permission Decorators

```python
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from accounts.models import get_teacher_or_student

def teacher_required(view_func):
    """Decorator to ensure user is a teacher."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        teacher, student = get_teacher_or_student(request.user)
        if not teacher:
            return HttpResponseForbidden("Teacher access required.")
        return view_func(request, *args, **kwargs)
    return wrapper

def student_required(view_func):
    """Decorator to ensure user is a student."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        teacher, student = get_teacher_or_student(request.user)
        if not student:
            return HttpResponseForbidden("Student access required.")
        return view_func(request, *args, **kwargs)
    return wrapper

def homework_owner_required(view_func):
    """Decorator to ensure teacher owns the homework."""
    @wraps(view_func)
    def wrapper(request, homework_id, *args, **kwargs):
        from homeworks.models import Homework
        homework = get_object_or_404(Homework, id=homework_id)
        teacher, student = get_teacher_or_student(request.user)
        
        if not teacher or homework.created_by != teacher:
            return HttpResponseForbidden("Access denied.")
        
        return view_func(request, homework, *args, **kwargs)
    return wrapper

def section_access_required(view_func):
    """Decorator to ensure user has access to section."""
    @wraps(view_func)
    def wrapper(request, section_id, *args, **kwargs):
        from homeworks.models import Section
        section = get_object_or_404(Section, id=section_id)
        teacher, student = get_teacher_or_student(request.user)
        
        if teacher and section.homework.created_by == teacher:
            # Teacher owns the homework
            return view_func(request, section, *args, **kwargs)
        elif student:
            # Student access
            return view_func(request, section, *args, **kwargs)
        else:
            return HttpResponseForbidden("Access denied.")
    return wrapper
```

## API Design

### 1. RESTful Endpoints

```python
# Main URLs
urlpatterns = [
    path('', views.home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# API URLs
urlpatterns = [
    # Homework management
    path('homeworks/', views.HomeworkListView.as_view(), name='homework-list'),
    path('homeworks/create/', views.HomeworkCreateView.as_view(), name='homework-create'),
    path('homeworks/<uuid:homework_id>/', views.HomeworkDetailView.as_view(), name='homework-detail'),
    path('homeworks/<uuid:homework_id>/edit/', views.HomeworkEditView.as_view(), name='homework-edit'),
    path('homeworks/<uuid:homework_id>/delete/', views.HomeworkDeleteView.as_view(), name='homework-delete'),
    
    # Section management
    path('homeworks/<uuid:homework_id>/sections/', views.SectionListView.as_view(), name='section-list'),
    path('homeworks/<uuid:homework_id>/sections/create/', views.SectionCreateView.as_view(), name='section-create'),
    path('sections/<uuid:section_id>/', views.SectionDetailView.as_view(), name='section-detail'),
    path('sections/<uuid:section_id>/edit/', views.SectionEditView.as_view(), name='section-edit'),
    path('sections/<uuid:section_id>/delete/', views.SectionDeleteView.as_view(), name='section-delete'),
    
    # Conversation management
    path('sections/<uuid:section_id>/conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('sections/<uuid:section_id>/conversations/start/', views.ConversationStartView.as_view(), name='conversation-start'),
    path('conversations/<uuid:conversation_id>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:conversation_id>/send/', views.MessageSendView.as_view(), name='message-send'),
    path('conversations/<uuid:conversation_id>/delete/', views.ConversationDeleteView.as_view(), name='conversation-delete'),
    
    # Teacher testing
    path('sections/<uuid:section_id>/test/', views.TeacherTestStartView.as_view(), name='teacher-test-start'),
    path('test-conversations/<uuid:conversation_id>/', views.TeacherTestConversationView.as_view(), name='teacher-test-conversation'),
    path('test-conversations/<uuid:conversation_id>/delete/', views.TeacherTestDeleteView.as_view(), name='teacher-test-delete'),
    
    # Submission management (now in conversations app)
    path('sections/<uuid:section_id>/submit/', views.SectionSubmitView.as_view(), name='section-submit'),
    path('submissions/<uuid:submission_id>/', views.SubmissionDetailView.as_view(), name='submission-detail'),
]
```

### 2. View Classes

```python
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from permissions.decorators import teacher_required, student_required

class HomeworkListView(LoginRequiredMixin, ListView):
    """Display homeworks based on user role."""
    model = Homework
    template_name = 'homeworks/homework_list.html'
    context_object_name = 'homeworks'
    
    def get_queryset(self):
        teacher, student = get_teacher_or_student(self.request.user)
        
        if teacher:
            return Homework.objects.filter(created_by=teacher).order_by('-created_at')
        elif student:
            return Homework.objects.filter(sections__isnull=False).distinct().order_by('-created_at')
        else:
            return Homework.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher, student = get_teacher_or_student(self.request.user)
        
        if student:
            # Add progress information for each homework
            for homework in context['homeworks']:
                homework.progress = SubmissionService.get_student_homework_progress(student, homework)
        
        return context

class SectionSubmitView(LoginRequiredMixin, View):
    """Submit a section with the selected conversation."""
    
    @student_required
    def post(self, request, section_id):
        section = get_object_or_404(Section, id=section_id)
        conversation_id = request.POST.get('conversation_id')
        
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                student=request.user.student_profile,
                section=section
            )
            
            submission = SubmissionService.submit_section(
                request.user,
                conversation
            )
            
            messages.success(request, f"Section '{section.title}' submitted successfully!")
            return redirect('section-detail', section_id=section_id)
            
        except Conversation.DoesNotExist:
            messages.error(request, "Invalid conversation selected.")
            return redirect('section-detail', section_id=section_id)

class TeacherTestStartView(LoginRequiredMixin, View):
    """Start a teacher test conversation for a section."""
    
    @teacher_required
    @section_access_required
    def post(self, request, section):
        try:
            conversation = ConversationService.start_conversation(
                request.user,
                section
            )
            messages.success(request, f"Test conversation started for '{section.title}'")
            return redirect('teacher-test-conversation', conversation_id=conversation.id)
        except Exception as e:
            messages.error(request, f"Failed to start test conversation: {e}")
            return redirect('section-detail', section_id=section.id)

class TeacherTestConversationView(LoginRequiredMixin, View):
    """View and interact with a teacher test conversation."""
    
    @teacher_required
    def get(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Ensure teacher owns this test conversation
        if not conversation.is_teacher_test or conversation.user != request.user:
            return HttpResponseForbidden("Access denied.")
        
        return render(request, 'conversations/teacher_test_conversation.html', {
            'conversation': conversation,
            'section': conversation.section,
            'homework': conversation.section.homework
        })
    
    @teacher_required
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        content = request.POST.get('content')
        
        if not content:
            messages.error(request, "Message content is required.")
            return redirect('teacher-test-conversation', conversation_id=conversation.id)
        
        try:
            ai_response = ConversationService.send_message(
                conversation, content, 'student'
            )
            messages.success(request, "Message sent successfully!")
        except Exception as e:
            messages.error(request, f"Failed to send message: {e}")
        
        return redirect('teacher-test-conversation', conversation_id=conversation.id)

class TeacherTestDeleteView(LoginRequiredMixin, View):
    """Delete a teacher test conversation."""
    
    @teacher_required
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Ensure teacher owns this test conversation
        if not conversation.is_teacher_test or conversation.user != request.user:
            return HttpResponseForbidden("Access denied.")
        
        try:
            ConversationService.delete_teacher_test_conversation(conversation)
            messages.success(request, "Test conversation deleted successfully!")
            return redirect('section-detail', section_id=conversation.section.id)
        except Exception as e:
            messages.error(request, f"Failed to delete test conversation: {e}")
            return redirect('teacher-test-conversation', conversation_id=conversation.id)
```

## Database Migrations

### 1. Initial Migration

```python
# 0001_initial.py
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    initial = True
    
    dependencies = []
    
    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(max_length=150, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=150)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        # ... other models
    ]
```

## Testing Strategy

### 1. Test Structure

```python
# tests/test_services.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from homeworks.services import HomeworkService
from homeworks.models import Homework, Section

class HomeworkServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testteacher',
            password='testpass123'
        )
        self.teacher = Teacher.objects.create(user=self.user)
        
        self.homework_data = {
            'title': 'Test Homework',
            'description': 'Test Description',
            'due_date': timezone.now() + timedelta(days=7),
            'sections': [
                {
                    'title': 'Section 1',
                    'content': 'Test content 1',
                    'order': 1,
                    'solution': 'Test solution 1'
                },
                {
                    'title': 'Section 2',
                    'content': 'Test content 2',
                    'order': 2,
                    'solution': 'Test solution 2'
                }
            ]
        }
    
    def test_create_homework_with_sections(self):
        """Test creating homework with multiple sections."""
        homework, sections = HomeworkService.create_homework_with_sections(
            self.homework_data, 
            self.teacher
        )
        
        self.assertEqual(homework.title, self.homework_data['title'])
        self.assertEqual(sections.count(), 2)
        self.assertEqual(sections[0].order, 1)
        self.assertEqual(sections[1].order, 2)
        self.assertIsNotNone(sections[0].solution)
        self.assertIsNotNone(sections[1].solution)
```

## Deployment Configuration

### 1. Production Settings

```python
# llteacher/production.py
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Database (SQLite for production as specified)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Performance Considerations

### 1. Database Optimization

```python
# Optimized queries with select_related and prefetch_related
class HomeworkService:
    @staticmethod
    def get_teacher_homework_with_stats(teacher):
        """Get homework with optimized queries for statistics."""
        return Homework.objects.filter(created_by=teacher).select_related(
            'llm_config'
        ).prefetch_related(
            'sections__submissions__student__user',
            'sections__conversations__messages'
        ).annotate(
            section_count=Count('sections'),
            submission_count=Count('sections__submissions'),
            active_conversation_count=Count('sections__conversations')
        )
```

### 2. Caching Strategy

```python
from django.core.cache import cache
from django.conf import settings

class CacheService:
    """Service for managing application caching."""
    
    @staticmethod
    def get_homework_progress(student_id, homework_id):
        """Get cached homework progress for a student."""
        cache_key = f"homework_progress:{student_id}:{homework_id}"
        progress = cache.get(cache_key)
        
        if progress is None:
            # Calculate progress and cache for 5 minutes
            progress = SubmissionService.get_student_homework_progress(student_id, homework_id)
            cache.set(cache_key, progress, 300)
        
        return progress
```

## Security Considerations

### 1. Input Validation

```python
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError

class Section(models.Model):
    # ... existing fields ...
    
    def clean(self):
        """Validate section data."""
        super().clean()
        
        # Ensure order is within homework's section limit
        if self.homework and self.order > 20:
            raise ValidationError("Maximum 20 sections allowed per homework.")
        
        # Ensure order is unique within homework
        if self.homework:
            existing_sections = Section.objects.filter(
                homework=self.homework,
                order=self.order
            ).exclude(id=self.id)
            
            if existing_sections.exists():
                raise ValidationError(f"Section with order {self.order} already exists.")
```

### 2. Permission Enforcement

```python
class SectionAccessMixin:
    """Mixin to ensure proper access to sections."""
    
    def dispatch(self, request, *args, **kwargs):
        section = self.get_object()
        teacher, student = get_teacher_or_student(request.user)
        
        if teacher and section.homework.created_by == teacher:
            return super().dispatch(request, *args, **kwargs)
        elif student:
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("Access denied.")
```

## Testable-First Architecture

### Overview

The system follows a testable-first approach where views return typed dataclasses instead of mixing business logic with presentation. This ensures:

1. **Separation of Concerns**: Business logic is separate from rendering
2. **Easy Testing**: Data generation methods can be tested independently
3. **Type Safety**: Clear data contracts with dataclasses
4. **Reusability**: Same data can be used for HTML, JSON, or other formats
5. **Maintainability**: Easy to modify data structure without touching templates

### Example: Homework List View

#### **Current Approach (Mixed Concerns)**:
```python
class HomeworkListView(LoginRequiredMixin, ListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher, student = get_teacher_or_student(self.request.user)
        
        if student:
            # Add progress information for each homework
            for homework in context['homeworks']:
                homework.progress = SubmissionService.get_student_homework_progress(student, homework)
        
        return context
```

#### **New Approach (Testable First)**:
```python
from dataclasses import dataclass
from typing import List, Optional
from django.http import HttpRequest

@dataclass
class SectionProgress:
    section_id: str
    title: str
    status: str  # 'not_started', 'in_progress', 'submitted', 'overdue'
    conversation_id: Optional[str] = None

@dataclass
class HomeworkListItem:
    id: str
    title: str
    description: str
    due_date: datetime
    section_count: int
    progress: Optional[List[SectionProgress]] = None

@dataclass
class HomeworkListData:
    homeworks: List[HomeworkListItem]
    user_type: str  # 'teacher' or 'student'
    total_count: int

class HomeworkListView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest):
        # Get typed data
        data = self._get_homework_list_data(request.user)
        
        # Single render call
        return render(request, 'homeworks/homework_list.html', {
            'data': data
        })
    
    def _get_homework_list_data(self, user) -> HomeworkListData:
        """Get typed data for homework list. Easy to test!"""
        teacher, student = get_teacher_or_student(user)
        
        if teacher:
            homeworks = Homework.objects.filter(created_by=teacher).order_by('-created_at')
            user_type = 'teacher'
        elif student:
            homeworks = Homework.objects.filter(sections__isnull=False).distinct().order_by('-created_at')
            user_type = 'student'
        else:
            homeworks = Homework.objects.none()
            user_type = 'unknown'
        
        # Build typed data
        homework_items = []
        for homework in homeworks:
            progress = None
            if student:
                progress = self._build_section_progress(student, homework)
            
            homework_item = HomeworkListItem(
                id=str(homework.id),
                title=homework.title,
                description=homework.description,
                due_date=homework.due_date,
                section_count=homework.section_count,
                progress=progress
            )
            homework_items.append(homework_item)
        
        return HomeworkListData(
            homeworks=homework_items,
            user_type=user_type,
            total_count=len(homework_items)
        )
    
    def _build_section_progress(self, student, homework) -> List[SectionProgress]:
        """Build typed section progress data. Easy to test!"""
        progress = []
        sections = homework.sections.order_by('order')
        
        for section in sections:
            try:
                submission = Submission.objects.filter(
                    conversation__user=student.user,
                    conversation__section=section
                ).first()
                
                if submission:
                    status = 'submitted'
                    conversation_id = str(submission.conversation.id)
                else:
                    if homework.is_overdue:
                        status = 'overdue'
                        conversation_id = None
                    else:
                        status = 'not_started'
                        conversation_id = None
            except Exception:
                status = 'not_started'
                conversation_id = None
            
            progress.append(SectionProgress(
                section_id=str(section.id),
                title=section.title,
                status=status,
                conversation_id=conversation_id
            ))
        
        return progress
```

### Benefits of This Approach

1. **Testable**: You can test `_get_homework_list_data()` with mock data
2. **Typed**: Clear data contracts with dataclasses
3. **Separated Concerns**: Business logic separate from rendering
4. **Reusable**: Data can be used for JSON API responses too
5. **Maintainable**: Easy to modify data structure without touching templates

### Testing Example

```python
def test_get_homework_list_data_student(self):
    """Test homework list data generation for students."""
    view = HomeworkListView()
    user = self.create_student_user()
    
    # Test the data generation method directly
    data = view._get_homework_list_data(user)
    
    # Assertions on typed data
    self.assertEqual(data.user_type, 'student')
    self.assertEqual(len(data.homeworks), 1)
    self.assertIsNotNone(data.homeworks[0].progress)
    self.assertEqual(data.homeworks[0].progress[0].status, 'not_started')
```

### Template Usage

```html
<!-- Template receives typed data -->
{% for homework in data.homeworks %}
    <div class="homework-item">
        <h3>{{ homework.title }}</h3>
        <p>{{ homework.description }}</p>
        <p>Due: {{ homework.due_date }}</p>
        <p>Sections: {{ homework.section_count }}</p>
        
        {% if homework.progress %}
            <div class="progress">
                {% for section in homework.progress %}
                    <span class="status-{{ section.status }}">
                        {{ section.title }}: {{ section.status }}
                    </span>
                {% endfor %}
            </div>
        {% endif %}
    </div>
{% endfor %}
```

## Future Enhancements

### 1. Phase 2 Features
- **Real-time Updates**: WebSocket support for live conversation updates
- **Advanced Analytics**: Teacher dashboard with student progress metrics
- **Assignment Templates**: Pre-built homework templates for common subjects
- **Mobile App**: Native mobile applications for iOS and Android

### 2. Phase 3 Features
- **Multi-language Support**: Internationalization for global use
- **Advanced LLM Features**: Support for multiple AI models and providers
- **Integration APIs**: RESTful APIs for third-party integrations
- **Advanced Reporting**: Detailed analytics and export capabilities

## Key Benefits of the Simplified Model

### 1. **Cleaner Data Relationships**
- **No Nullable Foreign Keys**: Every relationship is clear and unambiguous
- **Hierarchical Structure**: Homework → Section → Conversation → Submission flow is intuitive
- **Eliminated Redundancy**: Removed unnecessary fields and complex soft delete logic
- **Unified User Model**: Single user field in conversations, type determined by user profile
- **No Circular Dependencies**: Clean separation between homework structure and conversation/submission data

### 2. **Teacher Testing Capabilities**
- **Test Conversations**: Teachers can create test conversations to verify AI tutor quality
- **Separate Tracking**: Test conversations are clearly distinguished from student conversations
- **Easy Cleanup**: Teachers can delete test conversations when no longer needed
- **Quality Assurance**: Ensures homework assignments provide good AI guidance before students use them

### 3. **Simplified Business Logic**
- **Clear Ownership**: Each conversation belongs to exactly one student and one section
- **Straightforward Submissions**: Submission simply tracks which conversation represents the final work
- **Easier Queries**: No need to check multiple fields or handle nullable relationships
- **Logical Grouping**: Submissions are naturally grouped with conversations since they represent conversation state

### 4. **Better Performance**
- **Optimized Queries**: Simpler relationships mean faster database operations
- **Reduced Complexity**: Fewer edge cases and validation rules to process
- **Cleaner Caching**: Simpler data structures are easier to cache effectively

### 5. **Improved Maintainability**
- **Less Code**: Fewer fields and methods to maintain
- **Clearer Intent**: Each model has a single, well-defined purpose
- **Easier Testing**: Simpler models are easier to test and debug
- **Better Separation of Concerns**: Homework structure vs. conversation data are clearly separated

## Conclusion

LLTeacher v2 addresses the critical architectural flaws of v1 while maintaining the innovative core concept. The new design provides:

1. **Clean Data Model**: Simplified relationships with proper constraints
2. **Service Layer Architecture**: Business logic separated from presentation
3. **Improved Performance**: Optimized queries and caching strategy
4. **Better User Experience**: Streamlined workflows and progress tracking
5. **Maintainable Codebase**: Clear separation of concerns and proper testing

The system is designed to be scalable, maintainable, and user-friendly while preserving the revolutionary AI-guided learning approach that makes LLTeacher unique.

# Data Model Analysis

## Overview

The LLTeacher data model is built around three core concepts: **Users**, **Homework Assignments**, and **LLM Interactions**. While the model captures the essential relationships, it has several design issues that make the system fragile and difficult to maintain.

## Current Model Structure

### 1. User Management (`accounts` app)

```python
class User(AbstractUser):
    # Extends Django's AbstractUser with no additional fields
    
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    bio = models.TextField(blank=True)
    
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    progress_notes = models.TextField(blank=True)
```

**Strengths:**
- Clean separation of concerns between teachers and students
- Proper use of Django's AbstractUser
- Clear one-to-one relationships

**Weaknesses:**
- No validation that a user can't be both teacher and student
- Limited profile information
- No role-based permissions system

### 2. Homework Management (`homeworks` app)

```python
class Homework(models.Model):
    title = models.TextField()
    description = models.TextField()
    created_by = models.ForeignKey('accounts.Teacher', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField()

class Solution(models.Model):
    homework = models.OneToOneField(Homework, on_delete=models.CASCADE, related_name='solution')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StudentSubmission(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='submissions')
    status = models.TextField(choices=[...])
    grade = models.TextField(blank=True, null=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

class TeacherTestSubmission(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='teacher_test_submissions')
    teacher = models.ForeignKey('accounts.Teacher', on_delete=models.CASCADE, related_name='test_submissions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Strengths:**
- Clear separation between homework, solutions, and submissions
- Proper tracking of creation and update times
- Status tracking for student submissions

**Weaknesses:**
- `grade` field is TextField instead of proper grading system
- No validation that due_date is in the future
- TeacherTestSubmission seems redundant and confusing
- No versioning of homework assignments

### 3. LLM Interactions (`llm_interactions` app)

```python
class Conversation(models.Model):
    student_submission = models.ForeignKey('homeworks.StudentSubmission', null=True, blank=True)
    teacher_test_submission = models.ForeignKey('homeworks.TeacherTestSubmission', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    message_type = models.CharField(choices=[('text', 'Text Message'), ('r_code', 'R Code Execution')])
    r_code_execution = models.ForeignKey('RCodeExecution', null=True, blank=True)
    is_from_student = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class RCodeExecution(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='r_code_executions')
    code = models.TextField()
    output = models.TextField()
    error = models.TextField(blank=True, null=True)
    execution_time = models.DateTimeField(auto_now_add=True)
    execution_duration = models.FloatField(null=True, blank=True)

class LLMConfig(models.Model):
    name = models.TextField()
    api_key_variable = models.TextField()
    model_name = models.TextField()
    base_prompt = models.TextField()
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=500)
    is_active = models.BooleanField(default=False)
```

**Strengths:**
- Flexible conversation system that can handle different message types
- R code execution tracking
- Configurable LLM settings

**Weaknesses:**
- **Critical Issue**: Conversation model has nullable foreign keys to both submission types
- Complex validation logic in `clean()` method
- No clear ownership model for conversations
- R code execution is hardcoded (not generic for different programming languages)

## Major Design Problems

### 1. **Conversation Ownership Confusion**

The `Conversation` model has nullable foreign keys to both `StudentSubmission` and `TeacherTestSubmission`, which creates several issues:

- **Data Integrity**: A conversation could theoretically have both or neither submission
- **Complex Validation**: The `clean()` method tries to enforce "exactly one" but this is fragile
- **Query Complexity**: Need to check both fields to find conversations
- **Permission Logic**: Complex access control logic in views

### 2. **Inconsistent Data Types**

- `grade` field is `TextField` instead of proper grading system
- `status` field uses text choices instead of proper enum
- No constraints on due dates or other business rules

### 3. **Redundant Models**

`TeacherTestSubmission` seems to duplicate functionality that could be handled by the existing `StudentSubmission` model with a flag.

### 4. **Missing Business Logic**

- No validation that students can only submit to assigned homeworks
- No workflow state management
- No audit trail for changes
- No soft delete functionality

### 5. **Scalability Concerns**

- All text fields use `TextField` without length limits
- No indexing strategy for common queries
- No caching layer for frequently accessed data

## Data Flow Issues

### 1. **Submission Creation Flow**

The current flow for creating student submissions is complex and error-prone:

1. Student accesses homework
2. System checks if submission exists
3. If not, redirects to create submission
4. Submission creation creates conversation
5. Multiple redirects and state checks

### 2. **Conversation State Management**

Conversations can be in multiple states:
- Active (can send messages)
- Review (read-only)
- Teacher test mode

This creates complex conditional logic throughout the views.

### 3. **Permission Checking**

Every view needs to check:
- User type (teacher/student)
- Ownership of resources
- Access permissions
- Conversation state

This leads to repetitive and error-prone code.

## Recommendations for Redesign

### 1. **Simplify Conversation Model**

Use a single foreign key with a discriminator field:

```python
class Conversation(models.Model):
    submission = models.ForeignKey('homeworks.Submission', on_delete=models.CASCADE)
    submission_type = models.CharField(choices=[('student', 'Student'), ('teacher_test', 'Teacher Test')])
    # ... other fields
```

### 2. **Unified Submission Model**

Create a single submission model that can handle both student and teacher submissions:

```python
class Submission(models.Model):
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    submission_type = models.CharField(choices=[('student', 'Student'), ('teacher_test', 'Teacher Test')])
    # ... other fields
```

### 3. **Proper Enum Fields**

Use Django's choices or external enum libraries for status and type fields.

### 4. **Business Logic Layer**

Move complex business logic out of views into service classes or model methods.

### 5. **Audit Trail**

Add proper tracking for all changes and state transitions.

## Conclusion

While the current model captures the essential relationships and functionality, it suffers from over-complexity, inconsistent design patterns, and lack of proper constraints. The redesign should focus on:

1. **Simplicity**: Reduce the number of models and relationships
2. **Consistency**: Use consistent patterns throughout
3. **Integrity**: Add proper constraints and validation
4. **Maintainability**: Separate concerns and reduce coupling
5. **Scalability**: Design for future growth and performance

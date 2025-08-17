# LLTeacher v2 - Service Layer Components

The LLTeacher v2 application follows a testable-first architecture with a well-defined service layer. The following core services are needed to implement the functionality:

## 1. HomeworkService

Responsible for managing homework assignments and their sections.

### Data Contracts

```python
@dataclass
class SectionCreateData:
    title: str
    content: str
    order: int
    solution: Optional[str] = None

@dataclass
class HomeworkCreateData:
    title: str
    description: str
    due_date: Any  # datetime
    sections: List[SectionCreateData]
    llm_config: Optional[UUID] = None

@dataclass
class HomeworkCreateResult:
    homework_id: UUID
    section_ids: List[UUID]
    success: bool = True
    error: Optional[str] = None

@dataclass
class SectionProgressData:
    section_id: UUID
    title: str
    order: int
    status: str  # 'not_started', 'in_progress', 'submitted', 'overdue'
    conversation_id: Optional[UUID] = None

@dataclass
class HomeworkProgressData:
    homework_id: UUID
    sections_progress: List[SectionProgressData]
    completed_sections: int = 0
    total_sections: int = 0
```

### Methods

```python
@staticmethod
def create_homework_with_sections(data: HomeworkCreateData, teacher: Teacher) -> HomeworkCreateResult:
    """Create homework with multiple sections."""
    
@staticmethod
def get_student_homework_progress(student: Student, homework: Homework) -> HomeworkProgressData:
    """Get student's progress on a specific homework."""
    
@staticmethod
def get_homework_with_sections(homework_id: UUID) -> Optional[HomeworkDetailData]:
    """Get detailed homework data with all sections."""
    
@staticmethod
def update_homework(homework_id: UUID, data: HomeworkUpdateData) -> HomeworkUpdateResult:
    """Update homework and its sections."""
    
@staticmethod
def delete_homework(homework_id: UUID) -> bool:
    """Delete a homework and all related sections."""
```

## 2. ConversationService

Responsible for managing conversations between users and AI tutors, including teacher test conversations.

### Data Contracts

```python
@dataclass
class MessageData:
    id: UUID
    content: str
    message_type: str
    timestamp: datetime
    is_from_student: bool
    is_from_ai: bool
    is_system_message: bool

@dataclass
class ConversationData:
    id: UUID
    user_id: UUID
    section_id: UUID
    section_title: str
    created_at: datetime
    updated_at: datetime
    is_teacher_test: bool
    is_student_conversation: bool
    messages: Optional[List[MessageData]] = None

@dataclass
class ConversationStartResult:
    conversation_id: UUID
    initial_message_id: UUID
    section_id: UUID
    success: bool = True
    error: Optional[str] = None

@dataclass
class MessageSendResult:
    user_message_id: Optional[UUID] = None
    ai_message_id: Optional[UUID] = None
    ai_response: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

@dataclass
class CodeExecutionResult:
    code_message_id: Optional[UUID] = None
    result_message_id: Optional[UUID] = None
    has_error: bool = False
    success: bool = True
    error: Optional[str] = None
```

### Methods

```python
@staticmethod
def start_conversation(user: User, section: Section) -> ConversationStartResult:
    """Start a new conversation for a user on a section."""
    
@staticmethod
def send_message(conversation: Conversation, content: str, message_type: str = 'student') -> MessageSendResult:
    """Send a user message and get AI response."""
    
@staticmethod
def get_conversation_data(conversation_id: UUID) -> Optional[ConversationData]:
    """Get conversation data including messages."""
    
@staticmethod
def add_system_message(conversation: Conversation, content: str) -> Optional[UUID]:
    """Add a system message to the conversation."""
    
@staticmethod
def delete_teacher_test_conversation(conversation: Conversation) -> bool:
    """Delete a teacher test conversation."""
    
@staticmethod
def get_teacher_test_conversations(teacher: Teacher, section: Optional[Section] = None) -> List[ConversationData]:
    """Get teacher test conversations for a teacher."""
    
@staticmethod
def handle_r_code_execution(conversation: Conversation, code: str, output: str, error: Optional[str] = None) -> CodeExecutionResult:
    """Handle R code execution and add results to conversation."""
```

## 3. SubmissionService

Responsible for managing student submissions for sections.

### Data Contracts

```python
@dataclass
class SubmissionResult:
    submission_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    section_id: Optional[UUID] = None
    is_new: bool = True
    success: bool = True
    error: Optional[str] = None

@dataclass
class SubmissionData:
    id: UUID
    conversation_id: UUID
    section_id: UUID
    section_title: str
    student_id: UUID
    student_name: str
    submitted_at: datetime

@dataclass
class AutoSubmitResult:
    total_sections: int
    processed_sections: int
    created_submissions: int
    error_count: int
    details: List[Dict[str, Any]]
```

### Methods

```python
@staticmethod
def submit_section(user: User, conversation: Conversation) -> SubmissionResult:
    """Submit a section with the selected conversation."""
    
@staticmethod
def get_submission_data(submission_id: UUID) -> Optional[SubmissionData]:
    """Get detailed submission data."""
    
@staticmethod
def auto_submit_overdue_sections() -> AutoSubmitResult:
    """Automatically submit overdue sections for all students."""
    
@staticmethod
def get_student_submissions(student: Student) -> List[SubmissionData]:
    """Get all submissions for a student."""
```

## 4. LLMService

Responsible for configuring and interacting with language model APIs.

### Data Contracts

```python
@dataclass
class LLMConfigData:
    id: UUID
    name: str
    model_name: str
    api_key_variable: str
    base_prompt: str
    temperature: float
    max_tokens: int
    is_default: bool
    is_active: bool

@dataclass
class LLMResponseResult:
    response_text: str
    tokens_used: int
    success: bool = True
    error: Optional[str] = None
```

### Methods

```python
@staticmethod
def get_response(conversation: Conversation, content: str, message_type: str) -> str:
    """Generate an AI response based on conversation context."""
    
@staticmethod
def get_default_config() -> Optional[LLMConfigData]:
    """Get the default LLM configuration."""
    
@staticmethod
def create_config(data: dict) -> UUID:
    """Create a new LLM configuration."""
    
@staticmethod
def update_config(config_id: UUID, data: dict) -> bool:
    """Update an existing LLM configuration."""
```

## Implementation Notes

1. All services follow the testable-first approach with clear data contracts.
2. Error handling is implemented consistently across all services.
3. The R code execution is handled in the browser via WebAssembly, with results communicated back to the ConversationService.
4. File uploads are not supported in the current implementation.
5. Each service method should be independently testable with minimal dependencies.
6. Services should not depend on views or presentation logic.
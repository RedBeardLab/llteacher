"""
Homework Service

This module provides services for managing homework assignments and their sections.
Following a testable-first approach with typed data contracts.
"""
from dataclasses import dataclass
from typing import Any, List, Dict
from uuid import UUID
from enum import Enum
from django.db import transaction


class SectionStatus(str, Enum):
    """Enumeration of possible section status values."""
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    IN_PROGRESS_OVERDUE = 'in_progress_overdue'
    SUBMITTED = 'submitted'
    OVERDUE = 'overdue'

# Data Contracts
@dataclass
class SectionCreateData:
    title: str
    content: str
    order: int
    solution: str | None = None

@dataclass
class HomeworkCreateData:
    title: str
    description: str
    due_date: Any  # datetime
    sections: list[SectionCreateData]
    llm_config: UUID | None = None

@dataclass
class HomeworkCreateResult:
    homework_id: UUID
    section_ids: list[UUID]
    success: bool = True
    error: str | None = None

@dataclass
class SectionProgressData:
    section_id: UUID
    title: str
    order: int
    status: SectionStatus
    conversation_id: UUID | None = None

@dataclass
class HomeworkProgressData:
    homework_id: UUID
    sections_progress: list[SectionProgressData]

# Missing data contracts that need to be defined
@dataclass
class HomeworkDetailData:
    """Data contract for detailed homework information including sections"""
    id: UUID
    title: str
    description: str
    due_date: Any  # datetime
    created_by: UUID
    created_at: Any  # datetime
    updated_at: Any  # datetime
    llm_config: UUID | None = None
    sections: list[Any] | None = None  # Will be defined with a proper type

@dataclass
class HomeworkUpdateData:
    """Data contract for updating homework"""
    title: str | None = None
    description: str | None = None
    due_date: Any | None = None  # datetime
    llm_config: UUID | None = None
    sections_to_update: list[Any] | None = None  # Will be defined with proper type
    sections_to_create: list[SectionCreateData] | None = None
    sections_to_delete: list[UUID] | None = None

@dataclass
class HomeworkUpdateResult:
    """Result of updating a homework assignment"""
    success: bool = True
    error: str | None = None
    homework_id: UUID | None = None
    updated_section_ids: list[UUID] | None = None
    created_section_ids: list[UUID] | None = None
    deleted_section_ids: list[UUID] | None = None

class HomeworkService:
    """
    Service class for homework-related business logic.
    
    This service follows a testable-first approach with clear data contracts
    and properly typed methods for easier testing and maintenance.
    """
    
    @staticmethod
    def create_homework_with_sections(data: HomeworkCreateData, teacher: 'Teacher') -> HomeworkCreateResult:
        """
        Create a new homework assignment with multiple sections.
        
        Args:
            data: Typed data object containing homework details
            teacher: Teacher object who is creating the homework
            
        Returns:
            HomeworkCreateResult object with operation results
        """
        from .models import Homework, Section, SectionSolution
        
        # Validate data
        if not data.title.strip():
            return HomeworkCreateResult(
                homework_id=None,  # type: ignore
                section_ids=[],
                success=False,
                error="Title cannot be empty"
            )
        
        try:
            with transaction.atomic():
                # Create homework
                homework = Homework.objects.create(
                    title=data.title,
                    description=data.description,
                    due_date=data.due_date,
                    created_by=teacher,
                    llm_config_id=data.llm_config
                )
                
                # Create sections
                section_ids: list[UUID] = []
                for section_data in data.sections:
                    # Create section
                    section = Section.objects.create(
                        homework=homework,
                        title=section_data.title,
                        content=section_data.content,
                        order=section_data.order
                    )
                    
                    # Create solution if provided
                    if section_data.solution:
                        solution = SectionSolution.objects.create(
                            content=section_data.solution
                        )
                        section.solution = solution
                        section.save()
                    
                    section_ids.append(section.id)
                
                return HomeworkCreateResult(
                    homework_id=homework.id,
                    section_ids=section_ids
                )
        except Exception as e:
            # Return failure result with error
            return HomeworkCreateResult(
                homework_id=None,  # type: ignore
                section_ids=[],
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def get_student_homework_progress(student: 'Student', homework: 'Homework') -> HomeworkProgressData:
        """
        Get a student's progress on a specific homework assignment.
        
        Args:
            student: Student object
            homework: Homework object
            
        Returns:
            HomeworkProgressData with progress information
        """
        # Import here to avoid circular imports
        from conversations.models import Submission, Conversation
        
        sections = homework.sections.order_by('order')
        progress_items: list[SectionProgressData] = []
        
        for section in sections:
            try:
                # Check if student has submitted this section
                submission = Submission.objects.filter(
                    conversation__user=student.user,
                    conversation__section=section,
                    conversation__is_deleted=False
                ).first()
                
                if submission:
                    status: SectionStatus = SectionStatus.SUBMITTED
                    conversation_id: UUID | None = submission.conversation.id
                else:
                    # Check if student has started working (has conversations)
                    conversation = Conversation.objects.filter(
                        user=student.user,
                        section=section,
                        is_deleted=False
                    ).first()
                    
                    if conversation:
                        # Student has started working
                        if homework.is_overdue:
                            status = SectionStatus.IN_PROGRESS_OVERDUE  # Started but overdue
                        else:
                            status = SectionStatus.IN_PROGRESS  # Started and on time
                        conversation_id = conversation.id
                    else:
                        # Student hasn't started
                        if homework.is_overdue:
                            status = SectionStatus.OVERDUE  # Never started and overdue
                        else:
                            status = SectionStatus.NOT_STARTED  # Never started, still time
                        conversation_id = None
            except Exception:
                status = SectionStatus.NOT_STARTED
                conversation_id = None
            
            # Create progress data for this section
            progress_items.append(SectionProgressData(
                section_id=section.id,
                title=section.title,
                order=section.order,
                status=status,
                conversation_id=conversation_id
            ))
        
        # Create and return the overall progress data
        return HomeworkProgressData(
            homework_id=homework.id,
            sections_progress=progress_items
        )
    
    @staticmethod
    def get_homework_with_sections(homework_id: UUID) -> HomeworkDetailData | None:
        """
        Get detailed homework data with all its sections.
        
        Args:
            homework_id: UUID of the homework to retrieve
            
        Returns:
            HomeworkDetailData if found, None otherwise
        """
        from .models import Homework
        
        try:
            # Get homework with optimized query using select_related and prefetch_related
            homework = Homework.objects.select_related(
                'created_by', 
                'llm_config'
            ).prefetch_related(
                'sections__solution'
            ).get(id=homework_id)
            
            # Prepare sections data
            sections: List[Dict[str, Any]] = []
            for section in homework.sections.order_by('order'):
                section_data: Dict[str, Any] = {
                    'id': section.id,
                    'title': section.title,
                    'content': section.content,
                    'order': section.order,
                    'has_solution': section.solution is not None,
                    'solution_content': section.solution.content if section.solution else None,
                    'created_at': section.created_at,
                    'updated_at': section.updated_at
                }
                sections.append(section_data)
            
            # Create and return the detailed data
            return HomeworkDetailData(
                id=homework.id,
                title=homework.title,
                description=homework.description,
                due_date=homework.due_date,
                created_by=homework.created_by.id,
                created_at=homework.created_at,
                updated_at=homework.updated_at,
                llm_config=homework.llm_config.id if homework.llm_config else None,
                sections=sections
            )
        except Homework.DoesNotExist:
            return None
        except Exception:
            return None
    
    @staticmethod
    def update_homework(homework_id: UUID, data: HomeworkUpdateData) -> HomeworkUpdateResult:
        """
        Update a homework assignment and its sections.
        
        Args:
            homework_id: UUID of the homework to update
            data: Typed data object containing update information
            
        Returns:
            HomeworkUpdateResult with operation results
        """
        from .models import Homework, Section, SectionSolution
        
        try:
            with transaction.atomic():
                # Get the homework
                homework = Homework.objects.get(id=homework_id)
                
                # Update basic fields if provided
                if data.title is not None:
                    homework.title = data.title
                if data.description is not None:
                    homework.description = data.description
                if data.due_date is not None:
                    homework.due_date = data.due_date
                if data.llm_config is not None:
                    homework.llm_config_id = data.llm_config
                
                # Save homework changes
                homework.save()
                
                # Initialize tracking lists for sections
                updated_section_ids: List[UUID] = []
                created_section_ids: List[UUID] = []
                deleted_section_ids: List[UUID] = []
                
                # Delete sections if requested
                if data.sections_to_delete:
                    for section_id in data.sections_to_delete:
                        try:
                            section = Section.objects.get(id=section_id, homework=homework)
                            section.delete()
                            deleted_section_ids.append(section_id)
                        except Section.DoesNotExist:
                            pass  # Skip if section doesn't exist
                
                # Create new sections if requested
                if data.sections_to_create:
                    for section_data in data.sections_to_create:
                        # Create section
                        section = Section.objects.create(
                            homework=homework,
                            title=section_data.title,
                            content=section_data.content,
                            order=section_data.order
                        )
                        
                        # Create solution if provided
                        if section_data.solution:
                            solution = SectionSolution.objects.create(
                                content=section_data.solution
                            )
                            section.solution = solution
                            section.save()
                        
                        created_section_ids.append(section.id)
                
                # Update existing sections if requested
                if data.sections_to_update:
                    for section_update in data.sections_to_update:
                        try:
                            section = Section.objects.get(
                                id=section_update.get('id'), 
                                homework=homework
                            )
                            
                            # Update section fields
                            if 'title' in section_update:
                                section.title = section_update['title']
                            if 'content' in section_update:
                                section.content = section_update['content']
                            if 'order' in section_update:
                                section.order = section_update['order']
                            
                            # Update solution if provided
                            if 'solution' in section_update:
                                solution_content = section_update['solution']
                                if solution_content:
                                    # Create or update solution
                                    if section.solution:
                                        section.solution.content = solution_content
                                        section.solution.save()
                                    else:
                                        solution = SectionSolution.objects.create(
                                            content=solution_content
                                        )
                                        section.solution = solution
                                else:
                                    # Remove solution
                                    if section.solution:
                                        section.solution.delete()
                                        section.solution = None
                            
                            section.save()
                            updated_section_ids.append(section.id)
                        except Section.DoesNotExist:
                            pass  # Skip if section doesn't exist
                
                # Return success result with tracking information
                return HomeworkUpdateResult(
                    success=True,
                    homework_id=homework.id,
                    updated_section_ids=updated_section_ids,
                    created_section_ids=created_section_ids,
                    deleted_section_ids=deleted_section_ids
                )
        except Homework.DoesNotExist:
            return HomeworkUpdateResult(
                success=False,
                error=f"Homework with id {homework_id} not found"
            )
        except Exception as e:
            return HomeworkUpdateResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def delete_homework(homework_id: UUID) -> bool:
        """
        Delete a homework and all related sections.
        
        Args:
            homework_id: UUID of the homework to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        from .models import Homework
        
        try:
            homework = Homework.objects.get(id=homework_id)
            homework.delete()  # This will cascade delete all sections and solutions
            return True
        except Homework.DoesNotExist:
            return False
        except Exception:
            return False

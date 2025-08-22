"""
Views for the homeworks app.

This module provides views for managing homework assignments and their sections,
following the testable-first architecture with typed data contracts.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from django.forms import formset_factory

from django.views import View
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.contrib import messages

from llteacher.permissions.decorators import teacher_required, student_required

from .models import Homework, Section, SectionSolution
from .services import HomeworkService, HomeworkCreateData, SectionCreateData
from .forms import HomeworkForm, SectionForm, SectionFormSet


@dataclass
class HomeworkListItem:
    """Data structure for a single homework item in the list view."""
    id: UUID
    title: str
    description: str
    due_date: Any  # datetime
    section_count: int
    created_at: Any  # datetime
    is_overdue: bool
    progress: Optional[List[Dict[str, Any]]] = None


@dataclass
class HomeworkListData:
    """Data structure for the homework list view."""
    homeworks: List[HomeworkListItem]
    user_type: str  # 'teacher', 'student', or 'unknown'
    total_count: int
    has_progress_data: bool


class HomeworkListView(View):
    """
    View for listing homework assignments.
    
    For teachers: Shows homeworks they have created
    For students: Shows homeworks assigned to them with progress
    """
    
    @method_decorator(login_required, name='dispatch')
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle GET requests to display homework list."""
        # Get the appropriate data based on user type
        data = self._get_view_data(request.user)
        
        # Render the template with the data
        return render(request, 'homeworks/list.html', {'data': data})
    
    def _get_view_data(self, user) -> HomeworkListData:
        """
        Prepare data for the homework list view based on user type.
        
        Args:
            user: The current user
            
        Returns:
            HomeworkListData with homeworks and user type information
        """
        # Determine user type
        teacher_profile = getattr(user, 'teacher_profile', None)
        student_profile = getattr(user, 'student_profile', None)
        
        homeworks = []
        has_progress_data = False
        
        if teacher_profile:
            # Teacher view - show homeworks created by this teacher
            user_type = 'teacher'
            
            # Query homeworks created by this teacher
            homework_objects = Homework.objects.filter(
                created_by=teacher_profile
            ).order_by('-created_at').prefetch_related('sections')
            
            # Transform to view-specific data
            for homework in homework_objects:
                homeworks.append(HomeworkListItem(
                    id=homework.id,
                    title=homework.title,
                    description=homework.description,
                    due_date=homework.due_date,
                    section_count=homework.section_count,
                    created_at=homework.created_at,
                    is_overdue=homework.is_overdue,
                    progress=None  # No progress data needed for teacher view
                ))
            
        elif student_profile:
            # Student view - show homeworks with progress
            user_type = 'student'
            has_progress_data = True
            
            # For now, show all homeworks (in a real app, would filter by assignments)
            homework_objects = Homework.objects.all().order_by('-created_at').prefetch_related('sections')
            
            # Transform to view-specific data with progress
            for homework in homework_objects:
                # Get student's progress for this homework
                progress_data = HomeworkService.get_student_homework_progress(
                    student_profile,
                    homework
                )
                
                # Format progress data for the view
                progress = []
                for section_progress in progress_data.sections_progress:
                    progress.append({
                        'section_id': section_progress.section_id,
                        'title': section_progress.title,
                        'order': section_progress.order,
                        'status': section_progress.status,
                        'conversation_id': section_progress.conversation_id
                    })
                
                homeworks.append(HomeworkListItem(
                    id=homework.id,
                    title=homework.title,
                    description=homework.description,
                    due_date=homework.due_date,
                    section_count=homework.section_count,
                    created_at=homework.created_at,
                    is_overdue=homework.is_overdue,
                    progress=progress
                ))
                
        else:
            # Unknown user type
            user_type = 'unknown'
        
        # Create and return the view data
        return HomeworkListData(
            homeworks=homeworks,
            user_type=user_type,
            total_count=len(homeworks),
            has_progress_data=has_progress_data
        )


@dataclass
class SectionDetailData:
    """Data structure for a single section in the homework detail view."""
    id: UUID
    title: str
    content: str
    order: int
    has_solution: bool
    solution_content: Optional[str]


@dataclass
class HomeworkDetailData:
    """Data structure for the homework detail view."""
    id: UUID
    title: str
    description: str
    due_date: Any  # datetime
    created_by: UUID
    created_by_name: str
    created_at: Any  # datetime
    sections: List[SectionDetailData]
    is_overdue: bool
    user_type: str  # 'teacher', 'student', or 'unknown'
    can_edit: bool
    llm_config: Optional[Dict[str, Any]] = None


@dataclass
class HomeworkFormData:
    """Data structure for the homework form view."""
    form: Any  # HomeworkForm
    section_forms: Any  # FormSet
    user_type: str
    action: str  # 'create' or 'edit'
    is_submitted: bool = False
    errors: Dict[str, Any] = None


class HomeworkCreateView(View):
    """View for creating a new homework."""
    
    @method_decorator(login_required, name='dispatch')
    @method_decorator(teacher_required, name='dispatch')
    def dispatch(self, *args, **kwargs):
        """Ensure user is a logged-in teacher."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle GET requests to display the create form."""
        data = self._get_view_data(request)
        return render(request, 'homeworks/form.html', {'data': data})
    
    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle POST requests to process the form submission."""
        data = self._process_form_submission(request)
        
        if data.is_submitted:
            messages.success(request, "Homework created successfully!")
            return redirect('homeworks:detail', homework_id=data.form.instance.id)
        
        return render(request, 'homeworks/form.html', {'data': data})
    
    def _get_view_data(self, request: HttpRequest) -> HomeworkFormData:
        """Prepare data for the form view."""
        # Create an empty homework form
        form = HomeworkForm()
        
        # Create empty section form (we'll start with one)
        SectionFormset = formset_factory(SectionForm, extra=1, formset=SectionFormSet)
        section_formset = SectionFormset(prefix='sections')
        
        # Return form data
        return HomeworkFormData(
            form=form,
            section_forms=section_formset,
            user_type='teacher',
            action='create',
            is_submitted=False
        )
    
    def _process_form_submission(self, request: HttpRequest) -> HomeworkFormData:
        """Process the form submission."""
        # Create forms from POST data
        form = HomeworkForm(request.POST)
        
        SectionFormset = formset_factory(SectionForm, extra=0, formset=SectionFormSet)
        section_formset = SectionFormset(request.POST, prefix='sections')
        
        # Check form validity
        if form.is_valid() and section_formset.is_valid():
            # Create homework using service
            homework = form.save(commit=False)
            homework.created_by = request.user.teacher_profile
            homework.save()
            
            # Create sections
            section_data = []
            for section_form in section_formset.forms:
                if section_form.cleaned_data and not section_form.cleaned_data.get('DELETE', False):
                    # Extract data from form
                    section_data.append(SectionCreateData(
                        title=section_form.cleaned_data['title'],
                        content=section_form.cleaned_data['content'],
                        order=section_form.cleaned_data['order'],
                        solution=section_form.cleaned_data['solution']
                    ))
            
            # Use service to create homework with sections
            homework_data = HomeworkCreateData(
                title=homework.title,
                description=homework.description,
                due_date=homework.due_date,
                sections=section_data,
                llm_config=homework.llm_config.id if homework.llm_config else None
            )
            
            result = HomeworkService.create_homework_with_sections(
                homework_data,
                request.user.teacher_profile
            )
            
            if result.success:
                # Success - set created homework on form for redirect
                form.instance.id = result.homework_id
                
                # Return success data
                return HomeworkFormData(
                    form=form,
                    section_forms=section_formset,
                    user_type='teacher',
                    action='create',
                    is_submitted=True
                )
            else:
                # Service error
                messages.error(request, f"Error creating homework: {result.error}")
        
        # Form validation error or service error
        errors = {}
        if form.errors:
            errors['homework'] = form.errors
        if section_formset.errors:
            errors['sections'] = section_formset.errors
        if section_formset.non_form_errors():
            errors['formset'] = section_formset.non_form_errors()
        
        # Return form data with errors
        return HomeworkFormData(
            form=form,
            section_forms=section_formset,
            user_type='teacher',
            action='create',
            is_submitted=False,
            errors=errors
        )


class HomeworkDetailView(View):
    """
    View for displaying and editing a homework assignment.
    
    For teachers: Shows the homework with editing capabilities
    For students: Shows the homework with links to start working
    """
    
    @method_decorator(login_required, name='dispatch')
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest, homework_id: UUID) -> HttpResponse:
        """Handle GET requests to display homework detail."""
        # Get the appropriate data based on user type
        data = self._get_view_data(request.user, homework_id)
        
        # If homework not found, redirect to list view
        if data is None:
            return redirect('homeworks:list')
        
        # Render the template with the data
        return render(request, 'homeworks/detail.html', {'data': data})
    
    def _get_view_data(self, user, homework_id: UUID) -> Optional[HomeworkDetailData]:
        """
        Prepare data for the homework detail view based on user type.
        
        Args:
            user: The current user
            homework_id: The UUID of the homework to display
            
        Returns:
            HomeworkDetailData with homework details, or None if not found
        """
        # Determine user type
        teacher_profile = getattr(user, 'teacher_profile', None)
        student_profile = getattr(user, 'student_profile', None)
        
        # Get homework details using service
        homework_detail = HomeworkService.get_homework_with_sections(homework_id)
        
        if homework_detail is None:
            return None
            
        # Determine user type and permissions
        user_type = 'unknown'
        can_edit = False
        
        if teacher_profile:
            user_type = 'teacher'
            # Teacher can edit if they are the owner
            can_edit = str(teacher_profile.id) == str(homework_detail.created_by)
            
        elif student_profile:
            user_type = 'student'
            # Students can't edit homeworks
            can_edit = False
        
        # Format sections data
        sections = []
        for section_data in homework_detail.sections:
            sections.append(SectionDetailData(
                id=section_data['id'],
                title=section_data['title'],
                content=section_data['content'],
                order=section_data['order'],
                has_solution=section_data['has_solution'],
                solution_content=section_data['solution_content']
            ))
        
        # Get teacher name
        from accounts.models import Teacher
        teacher = Teacher.objects.filter(id=homework_detail.created_by).first()
        created_by_name = f"{teacher.user.first_name} {teacher.user.last_name}".strip() if teacher else "Unknown Teacher"
        
        # Create and return the view data
        return HomeworkDetailData(
            id=homework_detail.id,
            title=homework_detail.title,
            description=homework_detail.description,
            due_date=homework_detail.due_date,
            created_by=homework_detail.created_by,
            created_by_name=created_by_name,
            created_at=homework_detail.created_at,
            sections=sections,
            is_overdue=homework_detail.due_date < timezone.now(),
            user_type=user_type,
            can_edit=can_edit,
            llm_config={"id": homework_detail.llm_config} if homework_detail.llm_config else None
        )
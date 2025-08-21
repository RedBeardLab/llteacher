"""
Views for the homeworks app.

This module provides views for managing homework assignments and their sections,
following the testable-first architecture with typed data contracts.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from django.views import View
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Prefetch
from django.utils import timezone

from llteacher.permissions.decorators import teacher_required, student_required

from .models import Homework, Section
from .services import HomeworkService, HomeworkCreateData, SectionCreateData


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
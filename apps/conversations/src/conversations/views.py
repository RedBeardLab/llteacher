"""
Views for the conversations app.

This module provides views for managing conversations between users and AI tutors,
following the testable-first architecture with typed data contracts.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List
from uuid import UUID
from datetime import datetime

from django.views import View
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from homeworks.models import Section, Homework
from .models import Conversation, Message, Submission
from .services import ConversationService, SubmissionService


@dataclass
class ConversationStartFormData:
    """Data structure for the conversation start form view."""
    section_id: UUID
    section_title: str
    errors: Dict[str, str] = None


@dataclass
class ConversationStartViewData:
    """Data structure for rendering the conversation start view."""
    section_id: UUID
    section_title: str
    homework_id: UUID
    homework_title: str


@dataclass
class MessageViewData:
    """Data structure for message display in conversation detail view."""
    id: UUID
    content: str
    message_type: str
    timestamp: datetime
    is_from_student: bool
    is_from_ai: bool
    is_system_message: bool
    css_class: str  # For styling


@dataclass
class ConversationDetailData:
    """Data structure for the conversation detail view."""
    id: UUID
    section_id: UUID
    section_title: str
    homework_id: UUID
    homework_title: str
    messages: List[MessageViewData]
    can_submit: bool
    is_teacher_test: bool


class ConversationStartView(View):
    """View for starting a new conversation on a section."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest, section_id: UUID) -> HttpResponse:
        """Handle GET requests to display the conversation start form."""
        # Get the section (404 if not found)
        section = get_object_or_404(Section.objects.select_related('homework'), id=section_id)
        
        # Create view data
        view_data = self._get_view_data(section)
        
        # Render the form
        return render(request, 'conversations/start.html', {
            'view_data': view_data
        })
    
    def post(self, request: HttpRequest, section_id: UUID) -> HttpResponse:
        """Handle POST requests to start a new conversation."""
        # Get the section (404 if not found)
        section = get_object_or_404(Section.objects.select_related('homework'), id=section_id)
        
        # Start conversation using service
        result = ConversationService.start_conversation(request.user, section)
        
        if result.success:
            # Redirect to conversation detail
            messages.success(request, "Conversation started successfully.")
            return redirect('conversations:detail', conversation_id=result.conversation_id)
        else:
            # Show error message
            messages.error(request, result.error or "Failed to start conversation.")
            
            # Create view data
            view_data = self._get_view_data(section)
            
            # Render the form with errors
            return render(request, 'conversations/start.html', {
                'view_data': view_data,
                'error': result.error
            })
    
    def _get_view_data(self, section: Section) -> ConversationStartViewData:
        """Prepare data for rendering the conversation start form."""
        return ConversationStartViewData(
            section_id=section.id,
            section_title=section.title,
            homework_id=section.homework.id,
            homework_title=section.homework.title
        )


class ConversationDetailView(View):
    """Placeholder view for conversation details."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest, conversation_id: UUID) -> HttpResponse:
        """Handle GET requests to display the conversation."""
        # This is a placeholder for tests to pass - will be fully implemented in a future task
        return HttpResponse("Conversation Detail Page")
"""
Views for the conversations app.

This module provides views for managing conversations between users and AI tutors,
following the testable-first architecture with typed data contracts.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List, Any
from uuid import UUID
from datetime import datetime

from django.views import View
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import time

from homeworks.models import Section
from .models import Conversation, Submission
from .services import ConversationService, SubmissionService


@dataclass
class ConversationStartFormData:
    """Data structure for the conversation start form view."""
    section_id: UUID
    section_title: str
    errors: Optional[Dict[str, str]] = None


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


@dataclass
class MessageSendFormData:
    """Data structure for the message send form."""
    conversation_id: UUID
    content: str
    message_type: str = 'student'
    errors: Optional[Dict[str, str]] = None


@dataclass
class MessageSendResult:
    """Result of a message send operation."""
    success: bool
    conversation_id: UUID
    error: Optional[str] = None




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
    """View for viewing an existing conversation."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest, conversation_id: UUID) -> HttpResponse:
        """Handle GET requests to display the conversation."""
        # Get conversation data using service
        conversation_data = ConversationService.get_conversation_data(conversation_id, request.user)
        
        # Check if conversation exists
        if not conversation_data:
            messages.error(request, "Conversation not found.")
            # Raise 404 instead of trying to render 404.html directly
            raise Http404("Conversation not found.")
        
        # Check access permissions
        if not self._check_conversation_access(request.user, conversation_data):
            return HttpResponseForbidden("You don't have permission to view this conversation.")
        
        # Process message styling for display
        conversation_data = self._process_message_styling(conversation_data)
        
        # Render the conversation detail template
        return render(request, 'conversations/detail.html', {
            'conversation_data': conversation_data
        })
    
    def _check_conversation_access(self, user, conversation_data):
        """
        Check if the user has access to view this conversation.
        
        Args:
            user: The user trying to access the conversation
            conversation_data: ConversationData object
            
        Returns:
            Boolean indicating if access is allowed
        """
        # User owns the conversation
        if str(user.id) == str(conversation_data.user_id):
            return True
        
        # Teacher can view student conversations (but not other teachers)
        has_teacher_profile = hasattr(user, 'teacher_profile')
        if has_teacher_profile and not conversation_data.is_teacher_test:
            return True
            
        return False
    
    def _process_message_styling(self, conversation_data):
        """
        Process messages to add CSS styling based on message types.
        
        Args:
            conversation_data: ConversationData object
            
        Returns:
            ConversationData with updated message styling
        """
        if conversation_data.messages:
            for message in conversation_data.messages:
                # Assign CSS classes based on message type
                if message.is_from_student:
                    message.css_class = "message-student"
                elif message.is_from_ai:
                    message.css_class = "message-ai"
                elif message.is_system_message:
                    message.css_class = "message-system"
                else:
                    message.css_class = "message-default"
        
        return conversation_data


class MessageSendView(View):
    """View for sending messages in a conversation."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def post(self, request: HttpRequest, conversation_id: UUID) -> HttpResponse:
        """Handle POST requests to send a message."""
        # Get the conversation (404 if not found)
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user owns this conversation
        if conversation.user != request.user:
            return HttpResponseForbidden("You can only send messages in your own conversations.")
        
        # Parse and validate form data
        form_data = self._parse_form_data(request.POST, conversation_id)
        
        # Check for validation errors
        if form_data.errors:
            messages.error(request, "There were errors in your message.")
            return render(request, 'conversations/message_form.html', {
                'form_data': form_data,
                'conversation_id': conversation_id
            })
        
        # Send message using service
        result = ConversationService.send_message(
            conversation,
            form_data.content,
            form_data.message_type
        )
        
        if result.success:
            # Redirect to conversation detail
            messages.success(request, "Message sent successfully.")
            return redirect('conversations:detail', conversation_id=conversation_id)
        else:
            # Show error message
            messages.error(request, result.error or "Failed to send message.")
            
            # Add the error to form data
            if not form_data.errors:
                form_data.errors = {}
            form_data.errors['service'] = result.error or "Failed to send message."
            
            # Render the form with errors
            return render(request, 'conversations/message_form.html', {
                'form_data': form_data,
                'conversation_id': conversation_id
            })
    
    def _parse_form_data(self, post_data, conversation_id: UUID) -> MessageSendFormData:
        """
        Parse and validate form data.
        
        Args:
            post_data: POST data from request
            conversation_id: UUID of the conversation
            
        Returns:
            MessageSendFormData with validated data or errors
        """
        # Initialize errors dict
        errors = {}
        
        # Get and validate content
        content = post_data.get('content', '').strip()
        if not content:
            errors['content'] = "Message content is required."
        
        # Get message type (default to 'student')
        message_type = post_data.get('message_type', 'student').strip()
        if not message_type:
            message_type = 'student'
        
        # Create and return form data
        return MessageSendFormData(
            conversation_id=conversation_id,
            content=content,
            message_type=message_type,
            errors=errors if errors else None
        )


# Simple API Views for Real-time Chat

class MessageSendAPIView(View):
    """Simple API view for sending messages via AJAX."""
    
    @method_decorator(login_required)
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request: HttpRequest, conversation_id: UUID) -> JsonResponse:
        """Handle AJAX POST requests to send a message."""
        try:
            # Parse JSON data
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            message_type = data.get('message_type', 'student')
            
            # Validate input
            if not content:
                return JsonResponse({
                    'success': False,
                    'error': 'Message content is required.'
                }, status=400)
            
            # Get conversation and check permissions
            conversation = get_object_or_404(Conversation, id=conversation_id)
            if conversation.user != request.user:
                return JsonResponse({
                    'success': False,
                    'error': 'You can only send messages in your own conversations.'
                }, status=403)
            
            # Send message using existing service
            result = ConversationService.send_message(conversation, content, message_type)
            
            if result.success:
                return JsonResponse({
                    'success': True,
                    'user_message_id': str(result.user_message_id),
                    'ai_message_id': str(result.ai_message_id),
                    'ai_response': result.ai_response
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.error or 'Failed to send message.'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class MessagesAPIView(View):
    """Simple API view for getting conversation messages."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request: HttpRequest, conversation_id: UUID) -> JsonResponse:
        """Get messages for a conversation."""
        try:
            # Get conversation data using existing service
            conversation_data = ConversationService.get_conversation_data(conversation_id, request.user)
            
            if not conversation_data:
                return JsonResponse({'success': False, 'error': 'Conversation not found.'}, status=404)
            
            # Simple permission check
            if str(request.user.id) != str(conversation_data.user_id):
                return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
            
            # Serialize messages
            messages = []
            if conversation_data.messages:
                for msg in conversation_data.messages:
                    messages.append({
                        'id': str(msg.id),
                        'content': msg.content,
                        'message_type': msg.message_type,
                        'timestamp': msg.timestamp.isoformat(),
                        'is_from_student': msg.is_from_student,
                        'is_from_ai': msg.is_from_ai,
                        'is_system_message': msg.is_system_message
                    })
            
            return JsonResponse({
                'success': True,
                'messages': messages,
                'conversation_id': str(conversation_data.id)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class ConversationStreamView(View):
    """Server-Sent Events view for streaming LLM responses."""
    
    @method_decorator(login_required)
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request: HttpRequest, conversation_id: UUID) -> StreamingHttpResponse:
        """Stream LLM response via Server-Sent Events."""
        
        # this stream function does too much parsing, and authz and getting the message
        # can happen outside
        def stream_llm_response():
            try:
                # Parse JSON data
                data = json.loads(request.body)
                content = data.get('content', '').strip()
                message_type = data.get('message_type', 'student')
                
                # Validate input
                if not content:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Message content is required.'})}\n\n".encode('utf-8')
                    return
                
                # Get conversation and check permissions
                conversation = get_object_or_404(Conversation, id=conversation_id)
                if conversation.user != request.user:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Permission denied.'})}\n\n".encode('utf-8')
                    return
                
                # Create user message first
                from .models import Message
                user_message = Message.objects.create(
                    conversation=conversation,
                    content=content,
                    message_type=message_type
                )
                
                # Send user message confirmation
                yield f"data: {json.dumps({'type': 'user_message', 'message_id': str(user_message.id), 'content': content})}\n\n".encode('utf-8')
                
                # Create AI message placeholder
                ai_message = Message.objects.create(
                    conversation=conversation,
                    content="",
                    message_type='ai'
                )
                
                # Send AI message start
                yield f"data: {json.dumps({'type': 'ai_message_start', 'message_id': str(ai_message.id)})}\n\n".encode('utf-8')
                
                # Stream LLM response
                from llm.services import LLMService
                full_response = ""
                
                for token in LLMService.stream_response(conversation, content, message_type):
                    full_response += token
                    
                    # Update AI message in database
                    ai_message.content = full_response
                    ai_message.save()
                    
                    # Send token via SSE
                    yield f"data: {json.dumps({'type': 'ai_token', 'message_id': str(ai_message.id), 'token': token, 'content': full_response})}\n\n".encode('utf-8')
                
                # Send completion signal
                yield f"data: {json.dumps({'type': 'ai_message_complete', 'message_id': str(ai_message.id), 'final_content': full_response})}\n\n".encode('utf-8')
                
            except json.JSONDecodeError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid JSON data.'})}\n\n".encode('utf-8')
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode('utf-8')
        
        response = StreamingHttpResponse(stream_llm_response(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        return response


class ConversationSubmitView(View):
    """View for directly submitting a conversation."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def post(self, request: HttpRequest, conversation_id: UUID) -> HttpResponse:
        """Handle POST requests to submit the current conversation."""
        # Get the conversation and check permissions
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user owns this conversation
        if conversation.user != request.user:
            return HttpResponseForbidden("You can only submit your own conversations.")
        
        # Check if user is a student
        if not hasattr(request.user, 'student_profile'):
            return HttpResponseForbidden("Only students can submit conversations.")
        
        # Check if conversation is not deleted
        if conversation.is_deleted:
            messages.error(request, "Cannot submit a deleted conversation.")
            return redirect('conversations:detail', conversation_id=conversation_id)
        
        # Submit the conversation using service
        result = SubmissionService.submit_section(request.user, conversation)
        
        if result.success:
            # Redirect to section detail with success message
            messages.success(
                request, 
                f"Conversation submitted successfully for section '{conversation.section.title}'." +
                (" (Updated existing submission)" if not result.is_new else "")
            )
            return redirect('homeworks:section_detail', 
                            homework_id=conversation.section.homework.id, 
                            section_id=conversation.section.id)
        else:
            # Show error message and redirect back to conversation
            messages.error(request, result.error or "Failed to submit conversation.")
            return redirect('conversations:detail', conversation_id=conversation_id)


class ConversationDeleteAndRestartView(View):
    """View for deleting a conversation and starting a new one."""
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure user is logged in before accessing view."""
        return super().dispatch(*args, **kwargs)
    
    def post(self, request: HttpRequest, conversation_id: UUID) -> HttpResponse:
        """Handle POST requests to delete conversation and start new one."""
        # Get the conversation and check permissions
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user owns this conversation
        if conversation.user != request.user:
            return HttpResponseForbidden("You can only delete your own conversations.")
        
        # Store section info before deleting
        section = conversation.section
        
        # Delete the conversation (soft delete)
        conversation.soft_delete()
        
        # Start a new conversation for the same section
        result = ConversationService.start_conversation(request.user, section)
        
        if result.success:
            messages.success(request, "Previous conversation deleted and new one started.")
            return redirect('conversations:detail', conversation_id=result.conversation_id)
        else:
            messages.error(request, f"Error starting new conversation: {result.error}")
            return redirect('homeworks:detail', homework_id=section.homework.id)

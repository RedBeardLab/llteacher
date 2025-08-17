"""
Tests for the ConversationService class.

This module contains tests for the ConversationService following
the testing-first architecture approach.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
import uuid

from conversations.models import Conversation, Message, Submission
from conversations.services import (
    ConversationService,
    ConversationData,
    MessageData,
    ConversationStartResult,
    MessageSendResult,
    CodeExecutionResult
)
from homeworks.models import Homework, Section
from accounts.models import Teacher, Student

User = get_user_model()

class ConversationServiceTestCase(TestCase):
    """Base test case for ConversationService with common setup."""
    
    def setUp(self):
        """Set up test data."""
        # Create a teacher user
        self.teacher_user = User.objects.create_user(
            username='testteacher',
            email='teacher@example.com',
            password='password123'
        )
        self.teacher = Teacher.objects.create(user=self.teacher_user)
        
        # Create a student user
        self.student_user = User.objects.create_user(
            username='teststudent',
            email='student@example.com',
            password='password123'
        )
        self.student = Student.objects.create(user=self.student_user)
        
        # Create a homework with a section
        self.homework = Homework.objects.create(
            title="Test Homework",
            description="Test Description",
            due_date=timezone.now() + timedelta(days=7),
            created_by=self.teacher
        )
        
        self.section = Section.objects.create(
            homework=self.homework,
            title="Test Section",
            content="Test Content",
            order=1
        )


class TestConversationServiceStart(ConversationServiceTestCase):
    """Test cases for ConversationService.start_conversation method."""
    
    def test_start_conversation_student_success(self):
        """Test starting a conversation as a student successfully."""
        result = ConversationService.start_conversation(
            self.student_user,
            self.section
        )
        
        # Check result is of correct type and successful
        self.assertIsInstance(result, ConversationStartResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.conversation_id)
        self.assertIsNotNone(result.initial_message_id)
        self.assertEqual(result.section_id, self.section.id)
        
        # Check conversation was created with correct data
        conversation = Conversation.objects.get(id=result.conversation_id)
        self.assertEqual(conversation.user, self.student_user)
        self.assertEqual(conversation.section, self.section)
        
        # Check initial message was created
        message = Message.objects.get(id=result.initial_message_id)
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.message_type, Message.MESSAGE_TYPE_AI)
    
    def test_start_conversation_teacher_success(self):
        """Test starting a teacher test conversation successfully."""
        result = ConversationService.start_conversation(
            self.teacher_user,
            self.section
        )
        
        # Check result is successful
        self.assertTrue(result.success)
        
        # Get conversation and check is_teacher_test property
        conversation = Conversation.objects.get(id=result.conversation_id)
        self.assertTrue(conversation.is_teacher_test)
        self.assertFalse(conversation.is_student_conversation)
    
    def test_start_conversation_failure(self):
        """Test handling errors when starting a conversation."""
        # Create invalid section ID to force failure
        invalid_section = MagicMock()
        invalid_section.id = uuid.uuid4()  # This ID doesn't exist in the database
        
        result = ConversationService.start_conversation(
            self.student_user,
            invalid_section
        )
        
        # Check result indicates failure
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


class TestConversationServiceMessages(ConversationServiceTestCase):
    """Test cases for message-related methods."""
    
    def setUp(self):
        """Set up test data including a conversation."""
        super().setUp()
        
        # Create a conversation
        result = ConversationService.start_conversation(
            self.student_user,
            self.section
        )
        self.conversation_id = result.conversation_id
        self.conversation = Conversation.objects.get(id=self.conversation_id)
        
    @patch('llm.services.LLMService.get_response')
    def test_send_message_success(self, mock_llm_response):
        """Test sending a message and getting AI response successfully."""
        # Mock LLM response
        mock_llm_response.return_value = "This is a mock AI response."
        
        # Send message
        message_content = "Test message from student"
        result = ConversationService.send_message(
            self.conversation,
            message_content
        )
        
        # Check result
        self.assertIsInstance(result, MessageSendResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.user_message_id)
        self.assertIsNotNone(result.ai_message_id)
        self.assertEqual(result.ai_response, mock_llm_response.return_value)
        
        # Check messages were created
        user_message = Message.objects.get(id=result.user_message_id)
        ai_message = Message.objects.get(id=result.ai_message_id)
        
        self.assertEqual(user_message.content, message_content)
        self.assertEqual(user_message.message_type, 'student')
        self.assertEqual(ai_message.content, mock_llm_response.return_value)
        self.assertEqual(ai_message.message_type, Message.MESSAGE_TYPE_AI)
    
    def test_get_conversation_data(self):
        """Test retrieving conversation data with messages."""
        # Add a few messages
        message1 = Message.objects.create(
            conversation=self.conversation,
            content="Student message",
            message_type='student'
        )
        
        message2 = Message.objects.create(
            conversation=self.conversation,
            content="AI response",
            message_type='ai'
        )
        
        # Get conversation data
        conversation_data = ConversationService.get_conversation_data(self.conversation_id)
        
        # Check result
        self.assertIsInstance(conversation_data, ConversationData)
        self.assertEqual(conversation_data.id, self.conversation_id)
        self.assertEqual(conversation_data.user_id, self.student_user.id)
        self.assertEqual(conversation_data.section_id, self.section.id)
        
        # Check messages
        self.assertEqual(len(conversation_data.messages), 3)  # Initial + 2 new messages
        self.assertEqual(conversation_data.messages[1].id, message1.id)
        self.assertEqual(conversation_data.messages[1].content, message1.content)
        self.assertEqual(conversation_data.messages[2].id, message2.id)
        self.assertEqual(conversation_data.messages[2].content, message2.content)
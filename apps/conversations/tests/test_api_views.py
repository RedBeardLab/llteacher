"""
Tests for the conversations API views.

Testing the real-time chat functionality with a test-first approach.
"""
import json
from uuid import uuid4
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock

from homeworks.models import Homework, Section
from conversations.models import Conversation, Message
from accounts.models import Student, Teacher

User = get_user_model()


class MessageSendAPIViewTest(TestCase):
    """Test the AJAX message sending API."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create student profile
        self.student_profile = Student.objects.create(user=self.user)
        
        # Create teacher for homework
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123'
        )
        self.teacher = Teacher.objects.create(user=self.teacher_user)
        
        # Create homework and section
        from datetime import datetime
        self.homework = Homework.objects.create(
            title='Test Homework',
            description='Test description',
            created_by=self.teacher,
            due_date=datetime(2024, 12, 31)
        )
        
        self.section = Section.objects.create(
            homework=self.homework,
            title='Test Section',
            content='Test section content',
            order=1
        )
        
        # Create conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            section=self.section
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
    
    def test_send_message_success(self):
        """Test successful message sending via AJAX."""
        url = reverse('conversations:api_send_message', kwargs={'conversation_id': self.conversation.id})
        
        data = {
            'content': 'Hello, this is a test message',
            'message_type': 'student'
        }
        
        with patch('conversations.services.ConversationService.send_message') as mock_send:
            # Mock successful response
            mock_send.return_value = MagicMock(
                success=True,
                user_message_id=uuid4(),
                ai_message_id=uuid4(),
                ai_response='Hello! How can I help you?'
            )
            
            response = self.client.post(
                url,
                data=json.dumps(data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('user_message_id', response_data)
        self.assertIn('ai_message_id', response_data)
        self.assertIn('ai_response', response_data)
    
    def test_send_message_empty_content(self):
        """Test sending message with empty content."""
        url = reverse('conversations:api_send_message', kwargs={'conversation_id': self.conversation.id})
        
        data = {
            'content': '',
            'message_type': 'student'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_send_message_permission_denied(self):
        """Test sending message to conversation owned by another user."""
        # Create another user and conversation
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        other_conversation = Conversation.objects.create(
            user=other_user,
            section=self.section
        )
        
        url = reverse('conversations:api_send_message', kwargs={'conversation_id': other_conversation.id})
        
        data = {
            'content': 'This should fail',
            'message_type': 'student'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])


class MessagesAPIViewTest(TestCase):
    """Test the messages retrieval API."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create student profile
        self.student_profile = Student.objects.create(user=self.user)
        
        # Create teacher for homework
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123'
        )
        self.teacher = Teacher.objects.create(user=self.teacher_user)
        
        # Create homework and section
        from datetime import datetime
        self.homework = Homework.objects.create(
            title='Test Homework',
            description='Test description',
            created_by=self.teacher,
            due_date=datetime(2024, 12, 31)
        )
        
        self.section = Section.objects.create(
            homework=self.homework,
            title='Test Section',
            content='Test section content',
            order=1
        )
        
        # Create conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            section=self.section
        )
        
        # Create some messages
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            content='Hello',
            message_type='student'
        )
        
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            content='Hi there! How can I help?',
            message_type='ai'
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
    
    def test_get_messages_success(self):
        """Test successful message retrieval."""
        url = reverse('conversations:api_messages', kwargs={'conversation_id': self.conversation.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['messages']), 2)
        
        # Check message structure
        message = response_data['messages'][0]
        self.assertIn('id', message)
        self.assertIn('content', message)
        self.assertIn('message_type', message)
        self.assertIn('timestamp', message)
        self.assertIn('is_from_student', message)
        self.assertIn('is_from_ai', message)


class ConversationStreamViewTest(TestCase):
    """Test the Server-Sent Events stream."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create student profile
        self.student_profile = Student.objects.create(user=self.user)
        
        # Create teacher for homework
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='teacherpass123'
        )
        self.teacher = Teacher.objects.create(user=self.teacher_user)
        
        # Create homework and section
        from datetime import datetime
        self.homework = Homework.objects.create(
            title='Test Homework',
            description='Test description',
            created_by=self.teacher,
            due_date=datetime(2024, 12, 31)
        )
        
        self.section = Section.objects.create(
            homework=self.homework,
            title='Test Section',
            content='Test section content',
            order=1
        )
        
        # Create conversation
        self.conversation = Conversation.objects.create(
            user=self.user,
            section=self.section
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')

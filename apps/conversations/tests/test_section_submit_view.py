"""
Tests for the SectionSubmitView.

This module tests the functionality for submitting completed sections.
"""
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from uuid import UUID
from datetime import timedelta
from django.utils import timezone

from accounts.models import User, Teacher, Student
from homeworks.models import Homework, Section
from conversations.models import Conversation, Message, Submission


class SectionSubmitViewTests(TestCase):
    """Test cases for the SectionSubmitView."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a test user with teacher profile
        self.teacher_user = User.objects.create_user(
            username='teacheruser',
            email='teacher@example.com',
            first_name='Test',
            last_name='Teacher',
            password='password123'
        )
        self.teacher = Teacher.objects.create(user=self.teacher_user)
        
        # Create a test user with student profile
        self.student_user = User.objects.create_user(
            username='studentuser',
            email='student@example.com',
            first_name='Test',
            last_name='Student',
            password='password123'
        )
        self.student = Student.objects.create(user=self.student_user)
        
        # Create a test homework and section
        self.homework = Homework.objects.create(
            title="Test Homework",
            description="Test description",
            created_by=self.teacher,
            due_date=timezone.now() + timedelta(days=7)  # Due in 7 days
        )
        
        self.section = Section.objects.create(
            homework=self.homework,
            title="Test Section",
            content="Test content",
            order=1
        )
        
        # Create conversations for the student
        self.conversation1 = Conversation.objects.create(
            user=self.student_user,
            section=self.section
        )
        
        self.conversation2 = Conversation.objects.create(
            user=self.student_user,
            section=self.section
        )
        
        # Add messages to conversations
        Message.objects.create(
            conversation=self.conversation1,
            content="Initial AI message",
            message_type="ai"
        )
        
        Message.objects.create(
            conversation=self.conversation1,
            content="Student response",
            message_type="student"
        )
        
        Message.objects.create(
            conversation=self.conversation2,
            content="Initial AI message",
            message_type="ai"
        )
        
        # URL for submitting the section
        self.submit_url = reverse('conversations:submit_section', kwargs={
            'section_id': self.section.id
        })
    
    def test_submit_view_requires_login(self):
        """Test that submitting a section requires login."""
        response = self.client.get(self.submit_url)
        
        # Check that the user is redirected to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))
    
    def test_submit_view_requires_student_role(self):
        """Test that only students can submit sections."""
        # Login as teacher
        self.client.login(username='teacheruser', password='password123')
        
        # Attempt to access the submission page
        response = self.client.get(self.submit_url)
        
        # Check that access is forbidden for teachers
        self.assertEqual(response.status_code, 403)
    
    def test_student_can_view_submission_form(self):
        """Test that a student can view the section submission form."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Access the submission page
        response = self.client.get(self.submit_url)
        
        # Check response is successful
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'conversations/submit.html')
        
        # Check context data
        self.assertIsNotNone(response.context['view_data'])
        self.assertEqual(str(response.context['view_data'].section_id), str(self.section.id))
        self.assertEqual(response.context['view_data'].section_title, self.section.title)
        self.assertEqual(len(response.context['view_data'].conversations), 2)
    
    @patch('conversations.services.SubmissionService.submit_section')
    def test_student_can_submit_section(self, mock_submit_section):
        """Test that a student can submit a section with a selected conversation."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Mock the service response
        mock_result = MagicMock(
            success=True,
            submission_id=UUID('12345678-1234-5678-1234-567812345678'),
            conversation_id=self.conversation1.id,
            section_id=self.section.id,
            is_new=True
        )
        mock_submit_section.return_value = mock_result
        
        # Submit the section
        response = self.client.post(self.submit_url, {
            'conversation_id': self.conversation1.id
        })
        
        # Check that the service was called correctly
        mock_submit_section.assert_called_once()
        args = mock_submit_section.call_args[0]
        self.assertEqual(args[0], self.student_user)
        self.assertEqual(args[1].id, self.conversation1.id)
        
        # Check redirect to section detail
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('homeworks:section_detail', kwargs={
            'homework_id': self.homework.id,
            'section_id': self.section.id
        })
        self.assertEqual(response.url, expected_url)
    
    @patch('conversations.services.SubmissionService.submit_section')
    def test_submission_service_error(self, mock_submit_section):
        """Test error handling when submission service fails."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Mock service error response
        mock_result = MagicMock(
            success=False,
            error="Failed to submit section"
        )
        mock_submit_section.return_value = mock_result
        
        # Attempt to submit the section
        response = self.client.post(self.submit_url, {
            'conversation_id': self.conversation1.id
        })
        
        # Check that the form shows an error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Failed to submit section")
    
    def test_invalid_conversation_id(self):
        """Test handling of invalid conversation ID."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Submit with non-existent conversation ID
        response = self.client.post(self.submit_url, {
            'conversation_id': UUID('00000000-0000-0000-0000-000000000000')
        })
        
        # Check for error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid conversation selected")
    
    def test_section_does_not_exist(self):
        """Test the view behavior when the section does not exist."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Create URL with non-existent section ID
        non_existent_url = reverse('conversations:submit_section', kwargs={
            'section_id': UUID('00000000-0000-0000-0000-000000000000')
        })
        
        # Try to access the page
        response = self.client.get(non_existent_url)
        
        # Check response is a 404
        self.assertEqual(response.status_code, 404)
    
    def test_update_existing_submission(self):
        """Test updating an existing submission."""
        # Login as student
        self.client.login(username='studentuser', password='password123')
        
        # Create an existing submission
        submission = Submission.objects.create(
            conversation=self.conversation1
        )
        
        # Access the submission page
        response = self.client.get(self.submit_url)
        
        # Check that existing submission is in the context
        self.assertIsNotNone(response.context['view_data'].existing_submission)
        self.assertEqual(
            str(response.context['view_data'].existing_submission['conversation_id']), 
            str(self.conversation1.id)
        )
        
        # Update the submission with a different conversation
        with patch('conversations.services.SubmissionService.submit_section') as mock_submit_section:
            mock_result = MagicMock(
                success=True,
                submission_id=submission.id,
                conversation_id=self.conversation2.id,
                section_id=self.section.id,
                is_new=False
            )
            mock_submit_section.return_value = mock_result
            
            response = self.client.post(self.submit_url, {
                'conversation_id': self.conversation2.id
            })
            
            # Check that the service was called with the correct conversation
            mock_submit_section.assert_called_once()
            args = mock_submit_section.call_args[0]
            self.assertEqual(args[1].id, self.conversation2.id)
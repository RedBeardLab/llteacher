"""
Views for the accounts app.

This module provides views for user authentication and profile management,
following the testable-first architecture with typed data contracts.
"""
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID

from django.views import View
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.urls import reverse

from .forms import RegistrationForm
from .models import Teacher, Student, User


@dataclass
class RegistrationFormData:
    """Data structure for the registration form view."""
    username: str
    email: str
    password: str
    confirm_password: str
    role: str  # 'teacher' or 'student'
    errors: Dict[str, str] = None


@dataclass
class RegistrationResult:
    """Result of a registration attempt."""
    success: bool
    user_id: Optional[UUID] = None
    error: Optional[str] = None


class UserRegistrationView(View):
    """View for user registration (teacher/student)."""
    
    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle GET requests to display the registration form."""
        # Check if user is already logged in
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            # For testing purposes, avoid using a named URL that might not exist in test environment
            return redirect('/')
        
        # Create empty registration form
        form = RegistrationForm()
        
        # Render the form
        return render(request, 'accounts/register.html', {'form': form})
    
    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle POST requests to process registration form submission."""
        # Check if user is already logged in
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            # For testing purposes, avoid using a named URL that might not exist in test environment
            return redirect('/')
        
        # Process the form submission
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            result = self._register_user(form)
            
            if result.success:
                # Get the created user and log them in
                user = User.objects.get(id=result.user_id)
                login(request, user)
                
                messages.success(request, "Registration successful! You are now logged in.")
                # For testing purposes, avoid using a named URL that might not exist in test environment
                return redirect('/')
            else:
                messages.error(request, result.error or "Registration failed. Please try again.")
        
        # Render the form with errors
        return render(request, 'accounts/register.html', {'form': form})
    
    def _register_user(self, form) -> RegistrationResult:
        """
        Process user registration, creating appropriate profile based on role.
        
        Args:
            form: Valid RegistrationForm instance
            
        Returns:
            RegistrationResult with success status and user ID or error
        """
        try:
            with transaction.atomic():
                # Get form data
                role = form.cleaned_data['role']
                
                # Create user account (don't save yet)
                user = form.save(commit=False)
                
                # Set any additional user fields if needed
                user.email = form.cleaned_data['email']
                user.save()
                
                # Create role-specific profile
                if role == 'teacher':
                    Teacher.objects.create(user=user)
                elif role == 'student':
                    Student.objects.create(user=user)
                else:
                    # Invalid role
                    raise ValueError(f"Invalid role: {role}")
                
                # Set the backend for authentication
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                
                # We don't actually log in the user here because we don't have access to request
                
                # Return success result
                return RegistrationResult(
                    success=True,
                    user_id=user.id
                )
                
        except Exception as e:
            # Handle any errors
            return RegistrationResult(
                success=False,
                error=str(e)
            )
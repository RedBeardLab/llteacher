"""
URL patterns for the accounts app.
"""
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
]
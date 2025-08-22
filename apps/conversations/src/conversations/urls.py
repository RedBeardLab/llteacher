"""
URL patterns for the conversations app.
"""
from django.urls import path

from . import views

app_name = 'conversations'

urlpatterns = [
    path('section/<uuid:section_id>/start/', views.ConversationStartView.as_view(), name='start'),
    path('<uuid:conversation_id>/', views.ConversationDetailView.as_view(), name='detail'),
]
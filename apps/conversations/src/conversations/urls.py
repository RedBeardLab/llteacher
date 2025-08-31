"""
URL patterns for the conversations app.
"""
from django.urls import path

from . import views

app_name = 'conversations'

urlpatterns = [
    path('section/<uuid:section_id>/start/', views.ConversationStartView.as_view(), name='start'),
    path('section/<uuid:section_id>/submit/', views.SectionSubmitView.as_view(), name='submit_section'),
    path('<uuid:conversation_id>/', views.ConversationDetailView.as_view(), name='detail'),
    path('<uuid:conversation_id>/send/', views.MessageSendView.as_view(), name='send_message'),
    path('<uuid:conversation_id>/delete-and-restart/', views.ConversationDeleteAndRestartView.as_view(), name='delete_and_restart'),
    
    # API endpoints for real-time chat
    path('api/<uuid:conversation_id>/send-message/', views.MessageSendAPIView.as_view(), name='api_send_message'),
    path('api/<uuid:conversation_id>/messages/', views.MessagesAPIView.as_view(), name='api_messages'),
    path('api/<uuid:conversation_id>/stream/', views.ConversationStreamView.as_view(), name='api_stream'),
]

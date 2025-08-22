"""
URL patterns for the homeworks app.
"""
from django.urls import path

from . import views

app_name = 'homeworks'

urlpatterns = [
    path('', views.HomeworkListView.as_view(), name='list'),
    path('create/', views.HomeworkCreateView.as_view(), name='create'),
    path('<uuid:homework_id>/', views.HomeworkDetailView.as_view(), name='detail'),
    path('<uuid:homework_id>/edit/', views.HomeworkEditView.as_view(), name='edit'),
    path('<uuid:homework_id>/sections/<uuid:section_id>/', views.SectionDetailView.as_view(), name='section_detail'),
]
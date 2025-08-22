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
]
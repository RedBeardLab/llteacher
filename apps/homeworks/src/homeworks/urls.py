"""
URL patterns for the homeworks app.
"""
from django.urls import path

from . import views

app_name = 'homeworks'

urlpatterns = [
    path('', views.HomeworkListView.as_view(), name='list'),
    # These URLs will be implemented as we create the respective views
    path('create/', views.HomeworkListView.as_view(), name='create'),  # Placeholder
    path('<uuid:homework_id>/', views.HomeworkListView.as_view(), name='detail'),  # Placeholder
]
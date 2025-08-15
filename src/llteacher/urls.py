"""
URL configuration for llteacher project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Add your app URLs here
    # path('accounts/', include('accounts.urls')),
    # path('conversations/', include('conversations.urls')),
    # path('homeworks/', include('homeworks.urls')),
    # path('llm/', include('llm.urls')),
]

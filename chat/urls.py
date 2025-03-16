from django.urls import path

from . import views

urlpatterns = [
    path("<int:conversation_id>/", views.ConversationView.as_view(), name="conversation"),
]
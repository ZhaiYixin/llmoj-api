from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("conversations/", views.get_conversations, name="conversations"),
    path("conversations/<int:conversation_id>/messages/", views.get_messages, name="messages"),
    path("conversations/<int:conversation_id>/ask/", views.ask_question, name="ask"),
    path("conversations/<int:conversation_id>/answer/", views.get_answer, name="answer"),
    path("conversations/<int:conversation_id>/recommendations/", views.get_recommendations, name="recommendations"),
    path("conversations/start/", views.start_conversation, name="start"),
    path("templates/<int:template_id>/", views.get_template, name="template"),
]
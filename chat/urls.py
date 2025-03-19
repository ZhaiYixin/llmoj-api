from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("<int:conversation_id>/messages", views.get_messages, name="messages"),
    path("<int:conversation_id>/ask", views.ask_question, name="ask"),
    path("<int:conversation_id>/answer", views.get_answer, name="answer"),
    path("<int:conversation_id>/recommendations", views.get_recommendations, name="recommendations"),
]
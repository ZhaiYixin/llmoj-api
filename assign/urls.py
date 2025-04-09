from django.urls import path

from . import views

app_name = "assign"
urlpatterns = [
    path("classes/", views.ClassGroupView.as_view(), name="class_groups"),
    path("classes/<int:class_group_id>/", views.ClassGroupView.as_view(), name="class_group_detail"),
    path("assignments/", views.AssignmentView.as_view(), name="assignments"),
    path("assignments/<int:assignment_id>/", views.AssignmentView.as_view(), name="assignment_detail"),
    path("homeworks/", views.HomeworkView.as_view(), name="homeworks"),
    path("homeworks/<int:assignment_id>/", views.HomeworkView.as_view(), name="homework_detail"),
]
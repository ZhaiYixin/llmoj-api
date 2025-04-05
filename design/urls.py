from django.urls import path

from . import views

app_name = "design"
urlpatterns = [
    path("problems/", views.ProblemView.as_view(), name="problems"),
    path("problems/<int:problem_id>/", views.ProblemView.as_view(), name="problem_detail"),
    path("problem-lists/", views.ProblemListView.as_view(), name="problem_lists"),
    path("problem-lists/<int:problem_list_id>/", views.ProblemListView.as_view(), name="problem_list_detail"),
]
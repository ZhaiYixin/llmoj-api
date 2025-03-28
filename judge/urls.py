from django.urls import path

from . import views

app_name = "judge"
urlpatterns = [
    path("problems/", views.get_problems, name="problems"),
    path("problems/<int:problem_id>/testcases/", views.get_problem_testcases, name="testcases"),
    path("problems/<int:problem_id>/run/", views.run_code, name="run"),
    path("problems/<int:problem_id>/submit/", views.submit_code, name="submit"),
    path("problems/<int:problem_id>/submissions/", views.get_submissions, name="submissions"),
    path("problems/<int:problem_id>/results/", views.get_results, name="results"),
]
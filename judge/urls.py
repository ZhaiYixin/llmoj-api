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
    path("problems/<int:problem_id>/messages/", views.ProblemMessageView.as_view(), name="messages"),
    path("problems/<int:problem_id>/ask/", views.ProblemAskQuestionView.as_view(), name="ask"),
    path("problems/<int:problem_id>/answer/", views.ProblemGetAnswerView.as_view(), name="answer"),
    path("problems/<int:problem_id>/recommendations/", views.ProblemGetRecommendationsView.as_view(), name="recommendations"),
]
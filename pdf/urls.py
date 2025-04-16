from django.urls import path

from . import views

app_name = "pdf"
urlpatterns = [
    path("files/upload/", views.PDFFileUploadView.as_view(), name="upload"),
    path("files/<int:pdf_id>/", views.PDFFileView.as_view(), name="file_detail"),
    path("files/<int:pdf_id>/analysis/", views.PDFAnalysisView.as_view(), name="analysis"),
    path("files/<int:pdf_id>/messages/", views.PDFMessageView.as_view(), name="messages"),
    path("files/<int:pdf_id>/ask/", views.PDFAskQuestionView.as_view(), name="ask"),
    path("files/<int:pdf_id>/answer/", views.PDFGetAnswerView.as_view(), name="answer"),
]
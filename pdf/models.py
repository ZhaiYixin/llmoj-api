from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction

from chat.models import Conversation, Message

# Create your models here.
class PDF(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Page(models.Model):
    pdf = models.ForeignKey(PDF, related_name='pages', on_delete=models.CASCADE)
    page_number = models.IntegerField()
    content = models.TextField()

    def __str__(self):
        return f'Page {self.page_number} of {self.pdf.title}'

class Section(models.Model):
    pdf = models.ForeignKey(PDF, related_name='sections', on_delete=models.CASCADE)
    start_page = models.IntegerField()
    end_page = models.IntegerField()
    title = models.CharField(max_length=255, default='')
    description = models.TextField()
    questions = models.TextField(default='')
    
    def __str__(self):
        return f'Section {self.title} of {self.pdf.title} (page {self.start_page}-{self.end_page})'
    
    def clean(self):
        if self.start_page > self.end_page:
            raise ValidationError("Start page cannot be greater than end page.")
        if not self.pdf.pages.filter(page_number__gte=self.start_page, page_number__lte=self.end_page).exists():
            raise ValidationError("Page range is invalid for the selected PDF.")

class PDFConversation(models.Model):
    pdf = models.ForeignKey(PDF, related_name='conversations', on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, related_name='pdf_conversations', on_delete=models.CASCADE)

    def __str__(self):
        return f'Conversation {self.conversation.id} for PDF {self.pdf.title}'

    @classmethod
    def get_or_create_conversation(cls, pdf_id, user):
        with transaction.atomic():
            pdf_conversation = cls.objects.filter(pdf_id=pdf_id, conversation__user=user).first()
            if not pdf_conversation:
                conversation = Conversation.objects.create(user=user)
                pdf_conversation = cls.objects.create(pdf_id=pdf_id, conversation=conversation)
            return pdf_conversation

class PDFMessage(models.Model):
    pdf_conversation = models.ForeignKey(PDFConversation, related_name='messages', on_delete=models.CASCADE)
    page = models.ForeignKey(Page, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    section = models.ForeignKey(Section, related_name='messages', on_delete=models.CASCADE, null=True, blank=True)
    message = models.OneToOneField(Message, related_name='pdf_message', on_delete=models.CASCADE)
    
    def __str__(self):
        return f'Message {self.message.id} in page {self.page.page_number if self.page else "N/A"} of section {self.section.title if self.section else "N/A"} of PDF {self.pdf_conversation.pdf.title}'

    @classmethod
    def create_message(cls, pdf_conversation, role, content, tokens=0, page=None, section=None):
        with transaction.atomic():
            message = Message.objects.create(
                conversation=pdf_conversation.conversation,
                role=role,
                content=content,
                tokens=tokens
            )
            pdf_message = cls.objects.create(
                pdf_conversation=pdf_conversation,
                page=page,
                section=section,
                message=message
            )
        return pdf_message
from django.contrib import admin

from .models import PDF, Page, Section, PDFConversation, PDFMessage

# Register your models here.
admin.site.register(PDF)
admin.site.register(Page)
admin.site.register(Section)
admin.site.register(PDFConversation)
admin.site.register(PDFMessage)
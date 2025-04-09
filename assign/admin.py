from django.contrib import admin

from .models import ClassGroup, ClassMember, Assignment, Homework

# Register your models here.
admin.site.register(ClassGroup)
admin.site.register(ClassMember)
admin.site.register(Assignment)
admin.site.register(Homework)

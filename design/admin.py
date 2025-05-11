from django.contrib import admin

from .models import ProblemDesign, ProblemList, ProblemListItem

# Register your models here.
admin.site.register(ProblemDesign)
admin.site.register(ProblemList)
admin.site.register(ProblemListItem)

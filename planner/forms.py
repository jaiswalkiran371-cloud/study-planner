from django import forms
from django.contrib.auth.models import User
from .models import Course, StudentProfile

class StudySetupForm(forms.Form):
    exam_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    daily_hours = forms.DecimalField(min_value=0.5, max_value=16, decimal_places=1)
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.filter(active=True),
        widget=forms.CheckboxSelectMultiple
    )
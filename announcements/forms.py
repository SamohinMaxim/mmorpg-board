from django import forms
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Announcement, Response, NewsLetter, CATEGORY_CHOICES

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True})

    def value_from_datadict(self, data, files, name):
        if name in files:
            return files.getlist(name)
        return super().value_from_datadict(data, files, name)


class AnnouncementForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        label='Категория'
    )

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'category']



class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4}),
        }

class NewsLetterForm(forms.ModelForm):
    class Meta:
        model = NewsLetter
        fields = ['subject', 'content']

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

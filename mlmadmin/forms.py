import re
from django import forms
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.forms.fields import MultipleChoiceField
from django.utils.html import strip_tags
from mlmadmin.models import Recipient, MLM
from multifilefield.forms import MultiFileField


class RecipientForm(forms.ModelForm):

    class Meta:
        model = Recipient

    def __init__(self, *args, **kwargs):
        super(RecipientForm, self).__init__(*args, **kwargs)

        self.fields['mlm'].widget = forms.HiddenInput()
        self.fields['address'].widget = forms.Textarea(
            attrs={
                'rows': 10,
                'cols': 60})

        for field in self.fields.values():
            if field.required:
                field.label += '*'


class MultiEmailField(forms.Field):

    def to_python(self, value):
        "Normalize data to a list of strings."
        p = re.compile(
            r'[-!#$%&\'*+=?^_`{}|~]*[0-9A-Z]+[-!#$%&\'*+/=?^_`{}|~0-9A-Z.]*@[-0-9A-Z.]+\.[A-Z]{2,6}',
            re.IGNORECASE)

        # Return an empty list if no input was given.

        if not value:
            return []

        return [x.lower() for x in p.findall(value)]

    def validate(self, value):
        "Check if value consists only of valid emails."

        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)

        for email in value:
            try:
                validate_email(email)
            except:
                pass


class ComposeForm(forms.Form):
    sender = forms.EmailField()
    to = forms.MultipleChoiceField()
    subject = forms.CharField(
        max_length=4096,
        widget=forms.TextInput(
            attrs={
                'size': 60,
                'style': 'width:600px'}))
    body = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 10,
                'cols': 60}))
    files = MultiFileField(required=False)


class AddForm(forms.Form):
    address = MultiEmailField()
    mlm = forms.CharField(max_length=32)

    def save(self, delete=False):
        data = self.cleaned_data
        saved = {}
        success = []
        error = []
        mlm = MLM.objects.get(pk=data['mlm'])
        if delete:
            Recipient.objects.filter(mlm=mlm).delete()
        for i in data['address']:
            recipient = Recipient()
            recipient.mlm = mlm
            recipient.address = i
            try:
                recipient.save()
                success.append(i)
            except:
                error.append(i)
                pass
        return {'success': success, 'error': error}

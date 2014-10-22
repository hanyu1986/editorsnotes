from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models.auth import User, UserFeedback

PURPOSE_CHOICES = (
    ('1', 'Feedback'),
    ('2', 'Bug report'),
    ('3', 'Request for account'),
    ('9', 'Other')
)

class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=50, label='Your name')
    email = forms.EmailField(label='Your email')
    purpose = forms.ChoiceField(choices=PURPOSE_CHOICES)
    message = forms.CharField(widget=forms.Textarea(
        attrs={'cols': '50', 'rows': '7', 'style': 'width: 50em;' }))

class UserFeedbackForm(forms.models.ModelForm):
    class Meta:
        model = UserFeedback
        fields = '__all__'

class UserSignupForm(UserCreationForm):
    honeypot = forms.CharField(label="Username confirmation",
                               required=False,
                               widget=forms.TextInput(attrs={
                                   'id': 'username_confirmation',
                                   'placeholder': 'Omit if you are not a robot.',
                               }))
    arithmetic_answer = forms.CharField()
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(UserSignupForm, self).__init__(*args, **kwargs)

    def clean_arithmetic_answer(self):
        answer = self.cleaned_data.pop('arithmetic_answer', '')

        bad_answers = self.request.session.setdefault('bad_answers', 0)
        if bad_answers > 5:
            raise forms.ValidationError(
                'Too many failed attempts. Try again later.',
                code='bad_answers'
            )

        if answer.isdigit() and int(answer) == self.request.session['test_answer']:
            self.request.session.pop('bad_answers')

        else:
            self.request.session['bad_answers'] = bad_answers + 1
            raise forms.ValidationError('Incorrect answer.')

    # DELETE IN DJANGO 1.8
    # This is a clone of the clean_username method in Django's UserCreationForm,
    # which is removed in Django 1.8 in favor of performing this login in the
    # User model itself. We need to duplicate it because Django's method
    # hardcodes the non-custom User model.
    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            User._default_manager.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )

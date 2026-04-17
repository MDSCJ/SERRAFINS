from django import forms

from .models import Account


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if Account.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Account.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The passwords do not match.")
        return cleaned_data

    def save(self):
        account = Account(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            auth_provider=Account.AUTH_PROVIDER_LOCAL,
        )
        account.set_password(self.cleaned_data["password1"])
        account.set_initial_credits()
        account.save()
        return account

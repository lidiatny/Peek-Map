from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import Profile

# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        base = (
            "mt-1 w-full px-4 py-2.5 rounded-xl border border-gray-300 bg-white "
            "text-gray-900 shadow-sm focus:outline-none focus:ring-2 "
            "focus:ring-[#9A1E22] focus:border-[#9A1E22]"
        )
        pw = base + " pr-11"  # ada ruang untuk tombol eye

        self.fields["username"].widget.attrs.update({"class": base, "placeholder": "your_username"})
        self.fields["email"].widget.attrs.update({"class": base, "placeholder": "you@email.com"})
        self.fields["password1"].widget.attrs.update({"class": pw, "placeholder": "••••••••"})
        self.fields["password2"].widget.attrs.update({"class": pw, "placeholder": "••••••••"})


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-gray-900',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-gray-900',
                'placeholder': 'Email'
            }),
        }

class ProfileExtraForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'location', 'photo')
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'About me...',
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-gray-900'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'City, Country',
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-gray-900'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent text-gray-900'
            }),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={"class":"w-full rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"}),
            "email": forms.EmailInput(attrs={"class":"w-full rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["bio","location","photo"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows":4,"class":"w-full rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"}),
            "location": forms.TextInput(attrs={"class":"w-full rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"}),
            "photo": forms.ClearableFileInput(attrs={"class":"block w-full text-sm text-gray-700"}),
        }
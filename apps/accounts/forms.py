from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User
from django import forms
from django.contrib.auth import get_user_model

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')



# This automatically grabs  Custom User Model
User = get_user_model()
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'bio', 'avatar'] 
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style text fields
        for field_name, field in self.fields.items():
            # Apply standard styling to text inputs
            if field_name != 'avatar': 
                field.widget.attrs['class'] = 'w-full bg-slate-700 border border-slate-600 text-white text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-3 placeholder-gray-400'
        
        # Style the file input specifically (optional but looks better)
        self.fields['avatar'].widget.attrs['class'] = 'block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white file:hover:bg-indigo-700'
        
        self.fields['email'].disabled = True
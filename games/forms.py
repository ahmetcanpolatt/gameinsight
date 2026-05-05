from django import forms
from .models import Game

class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'platform', 'genre', 'price', 'purchase_date', 'playtime_hours', 'estimated_price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'genre': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'playtime_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'estimated_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }
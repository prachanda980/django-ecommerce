# apps/products/forms.py
from django import forms
from .models import ProductReview

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your experience with this product...',
                'class': 'w-full px-5 py-4 bg-slate-800/80 border border-slate-600 rounded-xl text-white focus:outline-none focus:border-indigo-500'
            }),
        }
        labels = {
            'rating': 'Your Rating',
            'comment': 'Review',
        }

    def __init__(self, *args, user=None, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.product = product
        self.fields['rating'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if self.user and self.product:
            if ProductReview.objects.filter(user=self.user, product=self.product).exists():
                raise forms.ValidationError("You have already reviewed this product.")
        return cleaned_data
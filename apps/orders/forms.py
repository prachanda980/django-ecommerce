from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'shipping_address',
            'billing_address',
            'customer_phone',
            'payment_method',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['billing_address'].required = False
        
        # Apply Tailwind classes for consistency
        common_classes = 'w-full px-6 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl text-white focus:outline-none focus:border-indigo-500 transition-all shadow-inner'
        
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': common_classes})
            
        # Add resize-none specifically for textareas
        self.fields['shipping_address'].widget.attrs['class'] += ' resize-none'
        self.fields['billing_address'].widget.attrs['class'] += ' resize-none'

    def clean(self):
        cleaned_data = super().clean()
        shipping_address = cleaned_data.get('shipping_address')
        billing_address = cleaned_data.get('billing_address')
        
        # LOGIC: If billing_address is empty (because it was hidden), 
        # use the shipping_address as the value.
        if not billing_address and shipping_address:
            cleaned_data['billing_address'] = shipping_address
            
        return cleaned_data
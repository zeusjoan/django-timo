from django import forms
from .models import Order, MonthlyReport, Overtime, UserProfile
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import models

class OrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Order
        fields = [
            'number',
            'description',
            'document_date',
            'delivery_date',
            'contract',
            'supplier_number',
            'budget_capex',
            'budget_opex',
            'budget_consultation',
            'hourly_rate',
            'attachment',
        ]
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'document_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'delivery_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'contract': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier_number': forms.TextInput(attrs={'class': 'form-control'}),
            'budget_capex': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'budget_opex': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'budget_consultation': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

class OrderCompleteForm(forms.Form):
    completion_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=True,
        label="Notatki zakończenia"
    )
    completion_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True,
        label="Data zakończenia",
        initial=datetime.now().date()
    )

class MonthlyReportForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        
        if self.order:
            # Używamy poprawnych nazw pól z modelu Order
            remaining_capex = self.order.budget_capex - (self.order.monthly_reports.aggregate(total=models.Sum('capex_hours'))['total'] or 0)
            remaining_opex = self.order.budget_opex - (self.order.monthly_reports.aggregate(total=models.Sum('opex_hours'))['total'] or 0)
            remaining_consultation = self.order.budget_consultation - (self.order.monthly_reports.aggregate(total=models.Sum('consultation_hours'))['total'] or 0)
            
            self.fields['capex_hours'].help_text = f'Dostępne: {remaining_capex:.1f}'
            self.fields['opex_hours'].help_text = f'Dostępne: {remaining_opex:.1f}'
            self.fields['consultation_hours'].help_text = f'Dostępne: {remaining_consultation:.1f}'

    month = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'month',
                'class': 'form-control',
                'required': True,
                'oninvalid': "this.setCustomValidity('Proszę wypełnić to pole')",
                'oninput': "this.setCustomValidity('')"
            }
        ),
        input_formats=['%Y-%m'],
    )

    def clean_invoice_number(self):
        invoice_number = self.cleaned_data.get('invoice_number')
        if not invoice_number or not invoice_number.strip():
            raise ValidationError("Numer faktury jest wymagany", code='error')
        return invoice_number.strip()

    def clean_month(self):
        month = self.cleaned_data.get('month')
        if isinstance(month, str):
            try:
                month = datetime.strptime(month + "-01", '%Y-%m-%d').date()
            except ValueError:
                raise forms.ValidationError("Nieprawidłowy format daty", code='error')

        if self.order and month.year != self.order.document_date.year:
            raise ValidationError(
                f"Rok rozliczenia ({month.year}) musi być zgodny z rokiem zamówienia ({self.order.document_date.year})",
                code='error'
            )

        if month and month.day != 1:
            month = month.replace(day=1)
        return month

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get('month')
        order = self.order

        if month and order:
            # Sprawdź czy istnieje już rozliczenie dla tego miesiąca i zamówienia
            existing_report = MonthlyReport.objects.filter(
                user=self.user,
                month__month=month.month,
                month__year=month.year,
                order=order
            ).exclude(pk=self.instance.pk if self.instance else None).first()

            if existing_report:
                raise forms.ValidationError(
                    f'Rozliczenie za {month.strftime("%B %Y")} dla tego zamówienia już istnieje.'
                )

        if self.order:
            capex_hours = cleaned_data.get('capex_hours', 0) or 0
            opex_hours = cleaned_data.get('opex_hours', 0) or 0
            consultation_hours = cleaned_data.get('consultation_hours', 0) or 0

            # Pobierz sumę godzin z istniejących raportów (z wyłączeniem bieżącego raportu, jeśli to edycja)
            existing_reports = self.order.monthly_reports.all()
            if self.instance.pk:
                existing_reports = existing_reports.exclude(pk=self.instance.pk)

            total_capex = existing_reports.aggregate(total=models.Sum('capex_hours'))['total'] or 0
            total_opex = existing_reports.aggregate(total=models.Sum('opex_hours'))['total'] or 0
            total_consultation = existing_reports.aggregate(total=models.Sum('consultation_hours'))['total'] or 0

            if total_capex + capex_hours > self.order.budget_capex:
                self.add_error('capex_hours', f'Przekroczono budżet CAPEX. Dostępne: {self.order.budget_capex - total_capex:.1f}')
            
            if total_opex + opex_hours > self.order.budget_opex:
                self.add_error('opex_hours', f'Przekroczono budżet OPEX. Dostępne: {self.order.budget_opex - total_opex:.1f}')
            
            if total_consultation + consultation_hours > self.order.budget_consultation:
                self.add_error('consultation_hours', f'Przekroczono budżet konsultacji. Dostępne: {self.order.budget_consultation - total_consultation:.1f}')

        return cleaned_data

    class Meta:
        model = MonthlyReport
        fields = [
            'month',
            'invoice_number',
            'capex_hours',
            'opex_hours',
            'consultation_hours',
            'invoice_file',
            'pzo_file'
        ]
        widgets = {
            'month': forms.DateInput(attrs={
                'type': 'month',
                'class': 'form-control',
                'required': True
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Wprowadź numer faktury',
                'oninvalid': "this.setCustomValidity('Proszę wypełnić to pole')",
                'oninput': "this.setCustomValidity('')"
            }),
            'capex_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0'
            }),
            'opex_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0'
            }),
            'consultation_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0'
            }),
            'invoice_file': forms.FileInput(attrs={'class': 'form-control'}),
            'pzo_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

class OvertimeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        super().__init__(*args, **kwargs)
        if not self.initial.get('start_time'):
            current_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M')
            self.initial['start_time'] = current_datetime
            self.initial['end_time'] = current_datetime

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if self.order and start_time and start_time.year != self.order.document_date.year:
            raise ValidationError(
                f"Rok nadgodzin ({start_time.year}) musi być zgodny z rokiem zamówienia ({self.order.document_date.year})",
                code='error'
            )
        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("Czas zakończenia musi być późniejszy niż czas rozpoczęcia.", code='error')
        
        if end_time and self.order and end_time.year != self.order.document_date.year:
            raise ValidationError(
                f"Rok nadgodzin ({end_time.year}) musi być zgodny z rokiem zamówienia ({self.order.document_date.year})",
                code='error'
            )
        
        return cleaned_data

    class Meta:
        model = Overtime
        exclude = ['user', 'hours', 'created_at', 'updated_at', 'order', 'status']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'required': True,
                    'oninvalid': "this.setCustomValidity('Proszę wypełnić to pole')",
                    'oninput': "this.setCustomValidity('')"
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local', 
                    'class': 'form-control',
                    'required': True,
                    'oninvalid': "this.setCustomValidity('Proszę wypełnić to pole')",
                    'oninput': "this.setCustomValidity('')"
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Opisz wykonane prace...',
                'required': True,
                'oninvalid': "this.setCustomValidity('Proszę wypełnić to pole')",
                'oninput': "this.setCustomValidity('')"
            }),
            'incident_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'INC000000'
            }),
            'type': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            })
        }

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, label="Imię")
    last_name = forms.CharField(max_length=30, label="Nazwisko")
    email = forms.EmailField(label="Email")

    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'position', 'department', 'employee_id', 'hire_date']
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            profile.save()
        return profile

class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput(), label="Obecne hasło")
    new_password1 = forms.CharField(widget=forms.PasswordInput(), label="Nowe hasło")
    new_password2 = forms.CharField(widget=forms.PasswordInput(), label="Powtórz nowe hasło")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Nieprawidłowe obecne hasło")
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("Nowe hasła nie są identyczne")
        return cleaned_data

    def save(self):
        new_password = self.cleaned_data['new_password1']
        self.user.set_password(new_password)
        self.user.save()
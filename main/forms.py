from django import forms
from .models import Order, MonthlyReport, Overtime, UserProfile
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

class OrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Order
        fields = [
            'number',
            'contract',
            'supplier_number',
            'document_date',
            'delivery_date',
            'hourly_rate',
            'capex_hours',
            'opex_hours',
            'consultation_hours',
            'attachment',
            'status'
        ]
        widgets = {
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'contract': forms.TextInput(attrs={'class': 'form-control'}),
            'supplier_number': forms.TextInput(attrs={'class': 'form-control'}),
            'document_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'capex_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'opex_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'consultation_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'})
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
            # Ustaw maksymalne wartości na podstawie pozostałego budżetu
            used_capex = MonthlyReport.objects.filter(order=self.order).aggregate(
                total=Sum('capex_hours'))['total'] or 0
            used_opex = MonthlyReport.objects.filter(order=self.order).aggregate(
                total=Sum('opex_hours'))['total'] or 0
            used_consultation = MonthlyReport.objects.filter(order=self.order).aggregate(
                total=Sum('consultation_hours'))['total'] or 0

            remaining_capex = float(self.order.capex_hours or 0) - float(used_capex)
            remaining_opex = float(self.order.opex_hours or 0) - float(used_opex)
            remaining_consultation = float(self.order.consultation_hours or 0) - float(used_consultation)

            self.fields['capex_hours'].widget.attrs['max'] = remaining_capex
            self.fields['opex_hours'].widget.attrs['max'] = remaining_opex
            self.fields['consultation_hours'].widget.attrs['max'] = remaining_consultation

            # Dodaj informacje o pozostałym budżecie w etykietach pól
            self.fields['capex_hours'].label = f'Godziny CAPEX (pozostało: {remaining_capex:.2f}h)'
            self.fields['opex_hours'].label = f'Godziny OPEX (pozostało: {remaining_opex:.2f}h)'
            self.fields['consultation_hours'].label = f'Godziny konsultacji (pozostało: {remaining_consultation:.2f}h)'

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
                # Lista polskich nazw miesięcy
                polish_months = {
                    1: 'stycznia', 2: 'lutego', 3: 'marca', 4: 'kwietnia',
                    5: 'maja', 6: 'czerwca', 7: 'lipca', 8: 'sierpnia',
                    9: 'września', 10: 'października', 11: 'listopada', 12: 'grudnia'
                }
                month_name = polish_months[month.month]
                raise forms.ValidationError(
                    f'Rozliczenie z {month_name} {month.year} dla tego zamówienia już istnieje.'
                )

        if self.order:
            capex_hours = cleaned_data.get('capex_hours', 0) or 0
            opex_hours = cleaned_data.get('opex_hours', 0) or 0
            consultation_hours = cleaned_data.get('consultation_hours', 0) or 0

            # Pobierz sumę godzin z istniejących raportów (z wyłączeniem bieżącego raportu, jeśli to edycja)
            existing_reports = self.order.monthly_reports.all()
            if self.instance.pk:
                existing_reports = existing_reports.exclude(pk=self.instance.pk)

            total_capex = existing_reports.aggregate(total=Sum('capex_hours'))['total'] or 0
            total_opex = existing_reports.aggregate(total=Sum('opex_hours'))['total'] or 0
            total_consultation = existing_reports.aggregate(total=Sum('consultation_hours'))['total'] or 0

            if total_capex + capex_hours > self.order.capex_hours:
                self.add_error('capex_hours', f'Przekroczono budżet CAPEX. Dostępne: {self.order.capex_hours - total_capex:.1f}')
            
            if total_opex + opex_hours > self.order.opex_hours:
                self.add_error('opex_hours', f'Przekroczono budżet OPEX. Dostępne: {self.order.opex_hours - total_opex:.1f}')
            
            if total_consultation + consultation_hours > self.order.consultation_hours:
                self.add_error('consultation_hours', f'Przekroczono budżet konsultacji. Dostępne: {self.order.consultation_hours - total_consultation:.1f}')

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
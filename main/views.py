from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.conf import settings
from django.db.models import Sum, Min, F, Value, CharField
from django.db.models.functions import TruncMonth, ExtractYear, ExtractMonth
from .forms import OrderForm, MonthlyReportForm, OvertimeForm, OrderCompleteForm, UserProfileForm, ChangePasswordForm
from .models import Order, MonthlyReport, Overtime, UserProfile
import pandas as pd
from io import BytesIO
import PyPDF2
import os
import json
from decimal import Decimal
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
import sqlite3

@login_required
def dashboard(request):
    current_year = timezone.now().year
    user = request.user
    
    # Pobieranie danych
    current_month = timezone.now().date().replace(day=1)
    thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)

    # Statystyki zamówień
    active_orders = Order.objects.filter(user=user, status='active').count()
    completed_orders = Order.objects.filter(user=user, status='completed').count()
    archived_orders = Order.objects.filter(user=user, status='archived').count()

    # Pobierz aktywne zamówienie i jego budżety
    active_order = Order.objects.filter(user=user, status='active').first()
    budget_capex = active_order.budget_capex if active_order else Decimal('0')
    budget_opex = active_order.budget_opex if active_order else Decimal('0')
    budget_consultation = active_order.budget_consultation if active_order else Decimal('0')

    # Nadgodziny z ostatnich 30 dni
    recent_overtime = Overtime.objects.filter(
        user=user,
        start_time__date__gte=thirty_days_ago
    ).aggregate(
        total_hours=Sum('hours')
    )['total_hours'] or Decimal('0')

    # Ostatnie nadgodziny do wyświetlenia w tabeli
    recent_overtimes = Overtime.objects.filter(
        user=user
    ).order_by('-start_time')[:5]

    # Dane do wykresu kołowego
    monthly_stats = MonthlyReport.objects.filter(
        user=user,
        month=current_month
    ).aggregate(
        capex=Sum('capex_hours'),
        opex=Sum('opex_hours'),
        consultation=Sum('consultation_hours')
    )

    capex_hours = monthly_stats['capex'] or Decimal('0')
    opex_hours = monthly_stats['opex'] or Decimal('0')
    consultation_hours = monthly_stats['consultation'] or Decimal('0')
    total_hours = capex_hours + opex_hours + consultation_hours

    if total_hours > 0:
        capex_usage_percent = (capex_hours / total_hours * Decimal('100')).quantize(Decimal('0.1'))
        opex_usage_percent = (opex_hours / total_hours * Decimal('100')).quantize(Decimal('0.1'))
    else:
        capex_usage_percent = Decimal('0')
        opex_usage_percent = Decimal('0')

    # Ostatnie 12 miesięcy
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=365)

    # Dane do wykresów
    months_data = MonthlyReport.objects.filter(
        user=user,
        month__range=[start_date, end_date]
    ).annotate(
        year=ExtractYear('month'),
        month_num=ExtractMonth('month')
    ).values('year', 'month_num').annotate(
        capex=Sum('capex_hours'),
        opex=Sum('opex_hours'),
        consultation=Sum('consultation_hours')
    ).order_by('year', 'month_num')

    months_labels = []
    capex_data = []
    opex_data = []
    consultation_data = []

    for data in months_data:
        months_labels.append(f"{data['year']}-{data['month_num']:02d}")
        capex_data.append(float(data['capex'] or 0))
        opex_data.append(float(data['opex'] or 0))
        consultation_data.append(float(data['consultation'] or 0))

    # Pobierz aktywne zamówienia
    active_orders_list = Order.objects.filter(
        user=user,
        status='active'
    ).order_by('-created_at')[:5]

    # Przygotuj dane do szablonu
    context = {
        'active_orders_count': active_orders,
        'completed_orders_count': completed_orders,
        'archived_orders_count': archived_orders,
        'recent_overtime': recent_overtime,
        'recent_overtimes': recent_overtimes,
        'active_orders': active_orders_list,
        'capex_hours': capex_hours,
        'opex_hours': opex_hours,
        'consultation_hours': consultation_hours,
        'total_hours': total_hours,
        'capex_usage_percent': capex_usage_percent,
        'opex_usage_percent': opex_usage_percent,
        'months_labels': months_labels,
        'capex_data': capex_data,
        'opex_data': opex_data,
        'consultation_data': consultation_data,
        'budget_capex': budget_capex,
        'budget_opex': budget_opex,
        'budget_consultation': budget_consultation,
    }

    return render(request, 'main/dashboard.html', context)

@login_required
def order_create(request):
    # Sprawdź czy nie ma już aktywnego zamówienia
    active_order = Order.objects.filter(user=request.user, status='active').first()
    if active_order:
        messages.error(request, f'Masz już aktywne zamówienie ({active_order.order_number}). Musisz je najpierw zakończyć.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.status = 'active'  # Ustawienie statusu na 'active'
            try:
                order.save()
                messages.success(request, 'Zamówienie zostało dodane.')
                return redirect('dashboard')
            except sqlite3.IntegrityError as e:
                messages.error(request, 'Błąd: Pole start_date nie może być puste. Proszę uzupełnić wszystkie wymagane pola.')
    else:
        form = OrderForm(user=request.user)
    return render(request, 'main/order_form.html', {'form': form})

@login_required
def order_edit(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES, instance=order, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Zamówienie zostało zaktualizowane.')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = OrderForm(instance=order, user=request.user)
    return render(request, 'main/order_form.html', {'form': form})

@login_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    try:
        order.delete()
        messages.success(request, 'Zamówienie zostało usunięte.')
    except Exception as e:
        messages.error(request, f'Nie można usunąć zamówienia: {str(e)}')
    return redirect('dashboard')

@login_required
def order_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != 'active':
        messages.error(request, 'Tylko aktywne zamówienie może zostać zakończone.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = OrderCompleteForm(request.POST)
        if form.is_valid():
            try:
                order.status = 'completed'
                order.completion_date = form.cleaned_data['completion_date']
                order.completion_notes = form.cleaned_data['completion_notes']
                order.save()
                
                # Zaktualizuj status powiązanych rozliczeń i nadgodzin
                MonthlyReport.objects.filter(order=order).update(status='completed')
                Overtime.objects.filter(order=order).update(status='completed')
                
                messages.success(request, f'Zamówienie {order.number} zostało zakończone.')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Wystąpił błąd podczas zamykania zamówienia: {str(e)}')
    else:
        form = OrderCompleteForm()
    
    return render(request, 'main/order_complete.html', {
        'form': form,
        'order': order
    })

@login_required
def order_reactivate(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == 'completed':
        messages.error(request, 'Nie można aktywować zrealizowanego zamówienia. Utwórz nowe zamówienie jeśli potrzebujesz.')
        return redirect('order_detail', order_id=order.id)
        
    try:
        if order.status == 'archived':
            order.status = 'active'
            order.save()
            messages.success(request, 'Zamówienie zostało aktywowane.')
        else:
            messages.warning(request, 'Można aktywować tylko zarchiwizowane zamówienia.')
    except Exception as e:
        messages.error(request, f'Wystąpił błąd podczas aktywacji zamówienia: {str(e)}')
    
    return redirect('order_detail', order_id=order.id)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/order_list.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
        'page_title': f'Zamówienie {order.number}',
    }
    return render(request, 'main/order_detail.html', context)

@login_required
def order_status_change(request, order_id, new_status):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if new_status in ['active', 'completed', 'archived']:
        order.status = new_status
        order.save()
        messages.success(request, 'Status zamówienia został zmieniony.')
    return redirect('order_list')

@login_required
def monthly_report_create(request):
    # Pobierz aktywne zamówienie
    active_order = Order.objects.filter(user=request.user, status='active').first()
    if not active_order:
        messages.error(request, 'Nie masz aktywnego zamówienia. Najpierw aktywuj lub utwórz nowe zamówienie.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = MonthlyReportForm(request.POST, request.FILES, user=request.user, order=active_order)
        if form.is_valid():
            try:
                report = form.save(commit=False)
                report.user = request.user
                report.order = active_order
                report.status = 'draft'
                report.save()
                messages.success(request, 'Rozliczenie zostało dodane.')
                return redirect('monthly_report_list')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = MonthlyReportForm(user=request.user, order=active_order)
    
    context = {
        'form': form,
        'active_order': active_order,
        'title': 'Nowe rozliczenie'
    }
    return render(request, 'main/monthly_report_form.html', context)

@login_required
def monthly_report_edit(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    if request.method == 'POST':
        form = MonthlyReportForm(
            request.POST, 
            request.FILES, 
            instance=report, 
            user=request.user,
            order=report.order
        )
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Rozliczenie zostało zaktualizowane.')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = MonthlyReportForm(
            instance=report, 
            user=request.user,
            order=report.order
        )
    return render(request, 'main/monthly_report_form.html', {'form': form})

@login_required
def monthly_report_delete(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    try:
        if report.merged_file:
            try:
                os.remove(report.merged_file.path)
            except Exception:
                pass  # Ignoruj błędy przy usuwaniu pliku
        report.delete()
        messages.success(request, 'Rozliczenie zostało usunięte.')
    except Exception as e:
        messages.error(request, f'Nie można usunąć rozliczenia: {str(e)}')
    return redirect('dashboard')

@login_required
def monthly_report_list(request):
    reports = MonthlyReport.objects.filter(user=request.user).order_by('-month')
    for report in reports:
        report.overtimes_sum = Overtime.objects.filter(
            user=request.user,
            start_time__year=report.month.year,
            start_time__month=report.month.month
        ).aggregate(Sum('hours'))['hours__sum'] or 0
    return render(request, 'main/monthly_report_list.html', {'reports': reports})

@login_required
def monthly_report_detail(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    overtimes_sum = Overtime.objects.filter(
        user=request.user,
        start_time__year=report.month.year,
        start_time__month=report.month.month
    ).aggregate(Sum('hours'))['hours__sum'] or 0
    return render(request, 'main/monthly_report_detail.html', {'report': report, 'overtimes_sum': overtimes_sum})

@login_required
def overtime_create(request):
    active_order = Order.objects.filter(user=request.user, status='active').first()
    print(f"Active order for overtime: {active_order}")  # Debugging
    if not active_order:
        messages.error(request, 'Nie można dodać nadgodzin. Brak aktywnego zamówienia.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = OvertimeForm(request.POST, order=active_order)
        if form.is_valid():
            try:
                overtime = form.save(commit=False)
                overtime.user = request.user
                overtime.order = active_order
                overtime.status = 'draft'
                overtime.save()
                messages.success(request, 'Nadgodziny zostały dodane.')
                return redirect('overtime_list')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Popraw błędy w formularzu.')
    else:
        form = OvertimeForm(order=active_order)
    
    context = {
        'form': form,
        'active_order': active_order
    }
    return render(request, 'main/overtime_form.html', context)

@login_required
def overtime_edit(request, overtime_id):
    overtime = get_object_or_404(Overtime, id=overtime_id, user=request.user)
    if request.method == 'POST':
        form = OvertimeForm(request.POST, instance=overtime, order=overtime.order)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Nadgodziny zostały zaktualizowane.')
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Popraw błędy w formularzu.')
    else:
        form = OvertimeForm(instance=overtime, order=overtime.order)
    return render(request, 'main/overtime_form.html', {'form': form})

@login_required
def overtime_delete(request, overtime_id):
    overtime = get_object_or_404(Overtime, id=overtime_id, user=request.user)
    try:
        overtime.delete()
        messages.success(request, 'Nadgodziny zostały usunięte.')
    except Exception as e:
        messages.error(request, f'Nie można usunąć nadgodzin: {str(e)}')
    return redirect('dashboard')

@login_required
def overtime_list(request):
    overtimes = Overtime.objects.filter(user=request.user).order_by('-start_time')
    return render(request, 'main/overtime_list.html', {'overtimes': overtimes})

@login_required
def overtime_detail(request, overtime_id):
    overtime = get_object_or_404(Overtime, id=overtime_id, user=request.user)
    return render(request, 'main/overtime_detail.html', {'overtime': overtime})

@login_required
def generate_merged_document(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    
    if not (report.invoice_file and report.pzo_file):
        messages.error(request, 'Brak wymaganych plików do połączenia (faktura i PZO)')
        return redirect('monthly_report_detail', report_id=report.id)
    
    try:
        # Przygotowanie ścieżek do plików
        invoice_path = report.invoice_file.path
        pzo_path = report.pzo_file.path
        
        # Przygotowanie nazwy pliku
        month_str = report.month.strftime('%Y-%m')
        invoice_part = f"_{report.invoice_number}" if report.invoice_number else ""
        merged_filename = f'Rozliczenie_{month_str}{invoice_part}.pdf'
        
        # Ścieżka do katalogu merged
        merged_dir = os.path.join(settings.MEDIA_ROOT, 'monthly_reports', 'merged')
        os.makedirs(merged_dir, exist_ok=True)
        
        # Pełna ścieżka do pliku wynikowego
        merged_path = os.path.join(merged_dir, merged_filename)
        
        # Łączenie plików PDF
        merger = PyPDF2.PdfMerger()
        merger.append(invoice_path)
        merger.append(pzo_path)
        
        # Zapisanie połączonego pliku
        with open(merged_path, 'wb') as output_file:
            merger.write(output_file)
        merger.close()
        
        # Aktualizacja modelu
        report.merged_file.name = f'monthly_reports/merged/{merged_filename}'
        report.save(update_fields=['merged_file'])
        
        messages.success(request, 'Dokumenty zostały pomyślnie połączone')
        return redirect('monthly_report_detail', report_id=report.id)
        
    except Exception as e:
        print(f"Szczegóły błędu łączenia plików: {str(e)}")
        messages.error(request, f'Wystąpił błąd podczas łączenia dokumentów: {str(e)}')
        return redirect('monthly_report_detail', report_id=report.id)

@login_required
def export_dashboard_data(request):
    # Utworzenie writera Excel
    output = BytesIO()
    
    # 1. Aktywne zamówienia
    active_orders = Order.objects.filter(
        user=request.user,
        status='active'
    ).values(
        'order_number',
        'client',
        'document_date',
        'capex_hours',
        'capex_budget',
        'opex_hours',
        'opex_budget'
    )

    # Utworzenie Excel writera z formatowaniem
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if active_orders:
            df_orders = pd.DataFrame(active_orders)
            df_orders['capex_usage'] = df_orders['capex_hours'] / df_orders['capex_budget']
            df_orders['opex_usage'] = df_orders['opex_hours'] / df_orders['opex_budget']
            df_orders.to_excel(writer, sheet_name='Aktywne zamówienia', index=False)

        # 2. Statystyki miesięczne
        monthly_stats = MonthlyReport.objects.filter(
            user=request.user,
            month__year=datetime.now().year
        ).values(
            'month',
            'capex_hours',
            'opex_hours',
            'consultation_hours'
        ).order_by('month')

        if monthly_stats:
            df_monthly = pd.DataFrame(monthly_stats)
            df_monthly['total_hours'] = df_monthly['capex_hours'] + df_monthly['opex_hours'] + df_monthly['consultation_hours']
            df_monthly.to_excel(writer, sheet_name='Statystyki miesięczne', index=False)

        # 3. Nadgodziny
        overtimes = Overtime.objects.filter(
            user=request.user,
            start_time__year=datetime.now().year
        ).values(
            'start_time',
            'end_time',
            'hours',
            'type',
            'status',
            'description'
        ).order_by('-start_time')

        if overtimes:
            df_overtime = pd.DataFrame(overtimes)
            df_overtime.to_excel(writer, sheet_name='Nadgodziny', index=False)

    # Przygotowanie odpowiedzi HTTP
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=dashboard_export_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return response

@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil został zaktualizowany.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'main/profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hasło zostało zmienione. Zaloguj się ponownie.')
            return redirect('login')
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'main/change_password.html', {'form': form})

@login_required
def monthly_report_status_change(request, report_id, new_status):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    if new_status in ['draft', 'sent', 'paid', 'completed', 'active']:
        report.status = new_status
        report.save()
        # Update the status of related overtime entries
        Overtime.objects.filter(
            user=request.user,
            start_time__year=report.month.year,
            start_time__month=report.month.month
        ).update(status=new_status)
        messages.success(request, 'Status rozliczenia został zmieniony.')
    return redirect('monthly_report_list')

@login_required
def overtime_status_change(request, overtime_id, new_status):
    overtime = get_object_or_404(Overtime, id=overtime_id, user=request.user)
    if new_status in ['draft', 'sent', 'paid', 'completed']:
        overtime.status = new_status
        overtime.save()
        messages.success(request, 'Status nadgodzin został zmieniony.')
    return redirect('overtime_list')

@login_required
def view_pdf(request, model_name, object_id, field_name):
    # Mapowanie nazw modeli na rzeczywiste modele
    models_map = {
        'order': Order,
        'monthly_report': MonthlyReport,
    }
    
    if model_name not in models_map:
        raise Http404("Nieprawidłowy typ dokumentu")
    
    model = models_map[model_name]
    obj = get_object_or_404(model, id=object_id, user=request.user)
    
    # Pobierz pole z plikiem PDF
    file_field = getattr(obj, field_name, None)
    if not file_field:
        raise Http404("Plik nie istnieje")
    
    try:
        # Sprawdź czy plik fizycznie istnieje
        if not os.path.exists(file_field.path):
            raise FileNotFoundError("Plik nie istnieje na dysku")
            
        response = FileResponse(file_field.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_field.name)}"'
        return response
    except Exception as e:
        print(f"Błąd podczas otwierania pliku {file_field.name}: {str(e)}")
        messages.error(request, f"Błąd podczas otwierania pliku: {str(e)}")
        return redirect('monthly_report_detail', report_id=object_id)

@login_required
def order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Tutaj dodaj logikę generowania PDF
    # Na razie zwracamy prosty response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="zamowienie_{order.number}.pdf"'
    
    # Przykład użycia reportlab do generowania PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # Nagłówek
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, f"Zamówienie {order.number}")
    
    # Informacje podstawowe
    p.setFont("Helvetica", 12)
    y = 750
    p.drawString(50, y, f"Status: {order.get_status_display()}")
    y -= 20
    p.drawString(50, y, f"Data utworzenia: {order.created_at.strftime('%d.%m.%Y %H:%M')}")
    y -= 20
    p.drawString(50, y, "Opis:")
    y -= 20
    p.drawString(50, y, order.description)
    
    # Budżet
    y -= 40
    p.drawString(50, y, "Budżet:")
    y -= 20
    p.drawString(50, y, f"CAPEX: {order.budget_capex} PLN")
    y -= 20
    p.drawString(50, y, f"OPEX: {order.budget_opex} PLN")
    y -= 20
    p.drawString(50, y, f"Konsultacje: {order.budget_consultation} PLN")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@login_required
def order_pdf_preview(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # Nagłówek
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, f"Zamówienie {order.number}")
    
    # Informacje podstawowe
    p.setFont("Helvetica", 12)
    y = 750
    p.drawString(50, y, f"Status: {order.get_status_display()}")
    y -= 20
    p.drawString(50, y, f"Data utworzenia: {order.created_at.strftime('%d.m.%Y %H:%M')}")
    y -= 20
    p.drawString(50, y, "Opis:")
    y -= 20
    p.drawString(50, y, order.description)
    
    # Budżet
    y -= 40
    p.drawString(50, y, "Budżet:")
    y -= 20
    p.drawString(50, y, f"CAPEX: {order.budget_capex} h")
    y -= 20
    p.drawString(50, y, f"OPEX: {order.budget_opex} h")
    y -= 20
    p.drawString(50, y, f"Konsultacje: {order.budget_consultation} h")
    
    p.showPage()
    p.save()
    
    # Get the value of the PDF
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline'  # This makes the browser try to display it
    response.write(pdf)
    
    return response

@login_required
def monthly_report_approve(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id, user=request.user)
    if report.status == 'completed':
        messages.info(request, 'To rozliczenie zostało już zatwierdzone.')
        return redirect('monthly_report_detail', report_id=report_id)

    # Update the status of related overtime entries
    Overtime.objects.filter(
        user=request.user,
        start_time__year=report.month.year,
        start_time__month=report.month.month
    ).update(status='completed')

    # Change the status of the report to 'completed'
    report.status = 'completed'
    report.save()
    messages.success(request, 'Rozliczenie zostało zatwierdzone.')
    return redirect('monthly_report_detail', report_id=report_id)

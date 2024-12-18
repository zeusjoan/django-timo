from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.conf import settings
from django.db.models import Min, F, Value, CharField
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

def calculate_total_value(user):
    """Oblicza całkowitą wartość dla aktywnych zamówień użytkownika"""
    active_orders = Order.objects.filter(
        user=user,
        status='active'
    )
    
    total_value = 0
    for order in active_orders:
        # Pobierz wartość z OrderValue jeśli istnieje
        order_value = getattr(order, 'order_value', None)
        if order_value:
            total_value += float(order_value.total_value or 0)
        else:
            # Jeśli nie ma OrderValue, oblicz na podstawie przepracowanych godzin i stawki
            hourly_rate = float(order.hourly_rate or 0)
            
            # Pobierz przepracowane godziny z rozliczeń
            reports = MonthlyReport.objects.filter(order=order)
            hours = reports.aggregate(
                total_hours=Sum(F('capex_hours') + F('opex_hours') + F('consultation_hours'))
            )['total_hours'] or 0
            
            # Dodaj nadgodziny
            overtimes = Overtime.objects.filter(order=order)
            overtime_hours = overtimes.aggregate(
                total_hours=Sum('hours')
            )['total_hours'] or 0
            
            total_value += (float(hours) + float(overtime_hours)) * hourly_rate
    
    return total_value

@login_required
def dashboard(request):
    # Pobierz aktywne zamówienie
    active_order = Order.objects.filter(user=request.user, status='active').first()
    
    context = {
        'total_value': calculate_total_value(request.user),
        'remaining_capex_hours': 0,
        'remaining_opex_hours': 0,
        'remaining_consultation_hours': 0,
        'used_capex_hours': 0,
        'used_opex_hours': 0,
        'used_consultation_hours': 0,
        'overtime_capex_hours': 0,
        'overtime_opex_hours': 0,
        'total_capex_hours': 0,
        'total_opex_hours': 0,
        'total_consultation_hours': 0,
        'total_used_capex_hours': 0,
        'total_used_opex_hours': 0,
        'capex_progress': 0,
        'opex_progress': 0,
        'consultation_progress': 0,
    }

    if active_order:
        # Pobierz zamówione godziny
        total_capex = float(active_order.capex_hours or 0)
        total_opex = float(active_order.opex_hours or 0)
        total_consultation = float(active_order.consultation_hours or 0)

        # Oblicz wykorzystane godziny tylko z rozliczonych raportów
        reports = MonthlyReport.objects.filter(
            order=active_order,
            status='completed'  # Status 'completed' dla rozliczonych raportów
        )
        used_capex = reports.aggregate(total=Sum('capex_hours'))['total'] or 0
        used_opex = reports.aggregate(total=Sum('opex_hours'))['total'] or 0
        used_consultation = reports.aggregate(total=Sum('consultation_hours'))['total'] or 0

        # Oblicz nadgodziny tylko z rozliczonych raportów
        overtimes = Overtime.objects.filter(
            order=active_order,
            status='completed'  # Status 'completed' dla rozliczonych nadgodzin
        )
        overtime_capex = overtimes.filter(type='capex').aggregate(total=Sum('hours'))['total'] or 0
        overtime_opex = overtimes.filter(type='opex').aggregate(total=Sum('hours'))['total'] or 0

        # Całkowite wykorzystane godziny (z raportów + nadgodziny)
        total_used_capex = float(used_capex) + float(overtime_capex)
        total_used_opex = float(used_opex) + float(overtime_opex)
        total_used_consultation = float(used_consultation)  # konsultacje nie mają nadgodzin

        # Oblicz pozostałe godziny (od zamówionych odejmujemy całkowite wykorzystane)
        remaining_capex = total_capex - total_used_capex
        remaining_opex = total_opex - total_used_opex
        remaining_consultation = total_consultation - total_used_consultation

        # Oblicz procent wykorzystania (wliczając nadgodziny)
        if total_capex:
            capex_progress = (total_used_capex / total_capex) * 100
        else:
            capex_progress = 0

        if total_opex:
            opex_progress = (total_used_opex / total_opex) * 100
        else:
            opex_progress = 0

        if total_consultation:
            consultation_progress = (total_used_consultation / total_consultation) * 100
        else:
            consultation_progress = 0

        context.update({
            'remaining_capex_hours': remaining_capex,
            'remaining_opex_hours': remaining_opex,
            'remaining_consultation_hours': remaining_consultation,
            'used_capex_hours': used_capex,
            'used_opex_hours': used_opex,
            'used_consultation_hours': used_consultation,
            'overtime_capex_hours': overtime_capex,
            'overtime_opex_hours': overtime_opex,
            'total_capex_hours': total_capex,
            'total_opex_hours': total_opex,
            'total_consultation_hours': total_consultation,
            'total_used_capex_hours': total_used_capex,
            'total_used_opex_hours': total_used_opex,
            'capex_progress': min(capex_progress, 100),
            'opex_progress': min(opex_progress, 100),
            'consultation_progress': min(consultation_progress, 100),
        })

    return render(request, 'main/dashboard.html', context)

@login_required
def order_create(request):
    # Sprawdź czy nie ma już aktywnego zamówienia
    active_order = Order.objects.filter(user=request.user, status='active').first()
    if active_order:
        messages.error(request, f'Masz już aktywne zamówienie ({active_order.number}). Musisz je najpierw zakończyć.')
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
            except ValidationError as e:
                messages.error(request, str(e))
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
    
    if order.status != Order.Status.ACTIVE:
        messages.error(request, 'Tylko aktywne zamówienie może zostać zakończone.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = OrderCompleteForm(request.POST)
        if form.is_valid():
            try:
                order.status = Order.Status.COMPLETED
                order.completion_date = form.cleaned_data['completion_date']
                order.completion_notes = form.cleaned_data['completion_notes']
                order.save()
                
                # Zaktualizuj status powiązanych rozliczeń i nadgodzin
                MonthlyReport.objects.filter(order=order).update(status=Order.Status.COMPLETED)
                Overtime.objects.filter(order=order).update(status=Order.Status.COMPLETED)
                
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
    
    if order.status == Order.Status.COMPLETED:
        messages.error(request, 'Nie można aktywować zrealizowanego zamówienia. Utwórz nowe zamówienie jeśli potrzebujesz.')
        return redirect('order_detail', order_id=order.id)
        
    try:
        if order.status == Order.Status.ARCHIVED:
            order.status = Order.Status.ACTIVE
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
    if new_status in [Order.Status.ACTIVE, Order.Status.COMPLETED, Order.Status.ARCHIVED]:
        order.status = new_status
        order.save()
        messages.success(request, 'Status zamówienia został zmieniony.')
    return redirect('order_list')

@login_required
def monthly_report_create(request):
    # Pobierz aktywne zamówienie
    active_order = Order.objects.filter(user=request.user, status=Order.Status.ACTIVE).first()
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
    active_order = Order.objects.filter(user=request.user, status=Order.Status.ACTIVE).first()
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
        status=Order.Status.ACTIVE
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
def export_dashboard(request):
    from openpyxl import Workbook
    from django.http import HttpResponse
    from datetime import datetime

    # Utworzenie nowego workbooka
    wb = Workbook()
    ws = wb.active
    ws.title = "Dashboard"

    # Nagłówki
    headers = ['Kategoria', 'Całkowity budżet', 'Wykorzystane', 'Nadgodziny', 'Pozostało', 'Procent wykorzystania']
    ws.append(headers)

    # Pobierz aktywne zamówienie
    active_order = Order.objects.filter(user=request.user, status='active').first()

    if active_order:
        # Oblicz statystyki tylko z rozliczonych raportów
        reports = MonthlyReport.objects.filter(
            order=active_order,
            status='completed'  # Status 'completed' dla rozliczonych raportów
        )
        used_capex = reports.aggregate(total=Sum('capex_hours'))['total'] or 0
        used_opex = reports.aggregate(total=Sum('opex_hours'))['total'] or 0
        used_consultation = reports.aggregate(total=Sum('consultation_hours'))['total'] or 0

        # Oblicz nadgodziny tylko z rozliczonych raportów
        overtimes = Overtime.objects.filter(
            order=active_order,
            status='completed'  # Status 'completed' dla rozliczonych nadgodzin
        )
        overtime_capex = overtimes.filter(type='capex').aggregate(total=Sum('hours'))['total'] or 0
        overtime_opex = overtimes.filter(type='opex').aggregate(total=Sum('hours'))['total'] or 0

        # Całkowite wykorzystane godziny (z raportów + nadgodziny)
        total_used_capex = float(used_capex) + float(overtime_capex)
        total_used_opex = float(used_opex) + float(overtime_opex)
        total_used_consultation = float(used_consultation)  # konsultacje nie mają nadgodzin

        # Oblicz pozostałe godziny (od zamówionych odejmujemy całkowite wykorzystane)
        remaining_capex = float(active_order.capex_hours or 0) - total_used_capex
        remaining_opex = float(active_order.opex_hours or 0) - total_used_opex
        remaining_consultation = float(active_order.consultation_hours or 0) - total_used_consultation

        # Przygotuj dane
        data = [
            ['CAPEX', 
             float(active_order.capex_hours or 0),
             total_used_capex,
             float(overtime_capex),
             remaining_capex,
             f"{(total_used_capex / float(active_order.capex_hours) * 100 if active_order.capex_hours else 0):.1f}%"],
            ['OPEX',
             float(active_order.opex_hours or 0),
             total_used_opex,
             float(overtime_opex),
             remaining_opex,
             f"{(total_used_opex / float(active_order.opex_hours) * 100 if active_order.opex_hours else 0):.1f}%"],
            ['Konsultacje',
             float(active_order.consultation_hours or 0),
             total_used_consultation,
             0,  # konsultacje nie mają nadgodzin
             remaining_consultation,
             f"{(total_used_consultation / float(active_order.consultation_hours) * 100 if active_order.consultation_hours else 0):.1f}%"]
        ]

        # Dodaj dane do arkusza
        for row in data:
            ws.append(row)

        # Formatowanie
        for col in range(1, 7):
            ws.column_dimensions[chr(64 + col)].width = 15

    # Przygotuj response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    # Zapisz do response
    wb.save(response)
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

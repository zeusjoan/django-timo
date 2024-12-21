from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .models import Order, MonthlyReport, Overtime, MonthlyReportSummary, OrderValue
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q as models

def calculate_total_value(user):
    """Oblicza sumę wartości dla aktywnych zamówień."""
    from django.db.models import Sum
    from .models import OrderValue

    total = OrderValue.objects.filter(
        order__user=user,
        order__status=Order.Status.ACTIVE
    ).aggregate(
        total=Sum('total_value')
    )['total'] or 0

    print(f"\nDEBUG - Wartości zamówień:")
    order_values = OrderValue.objects.filter(
        order__user=user,
        order__status=Order.Status.ACTIVE
    )
    
    for value in order_values:
        print(f"\nZamówienie: {value.order.number}")
        print(f"CAPEX: {value.capex_hours}h")
        print(f"OPEX: {value.opex_hours}h")
        print(f"Konsultacje: {value.consultation_hours}h")
        print(f"Stawka: {value.order.hourly_rate} PLN/h")
        print(f"Wartość: {value.total_value} PLN")

    print(f"\nŁączna wartość wszystkich aktywnych zamówień: {total} PLN")
    return total

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'main/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Ostatnie 12 miesięcy
        end_date = timezone.now()
        start_date = end_date - timedelta(days=365)

        # Podsumowanie godzin z raportów miesięcznych
        monthly_stats = MonthlyReport.objects.filter(
            user=user,
            month__range=(start_date, end_date)
        ).annotate(
            month=TruncMonth('month')
        ).values('month').annotate(
            total_capex=Sum('capex_hours'),
            total_opex=Sum('opex_hours'),
            total_consultation=Sum('consultation_hours')
        ).order_by('month')

        # Przygotowanie danych dla wykresu
        months = []
        capex_data = []
        opex_data = []
        consultation_data = []

        for stat in monthly_stats:
            months.append(stat['month'].strftime('%Y-%m'))
            capex_data.append(float(stat['total_capex'] or 0))
            opex_data.append(float(stat['total_opex'] or 0))
            consultation_data.append(float(stat['total_consultation'] or 0))

        # Statystyki zamówień
        active_orders = Order.objects.filter(user=user, status=Order.Status.ACTIVE).count()
        completed_orders = Order.objects.filter(user=user, status=Order.Status.COMPLETED).count()
        archived_orders = Order.objects.filter(user=user, status=Order.Status.ARCHIVED).count()

        # Nadgodziny w ostatnim miesiącu
        last_month = timezone.now() - timedelta(days=30)
        recent_overtime = Overtime.objects.filter(
            user=user,
            start_time__gte=last_month
        ).aggregate(
            total_hours=Sum('hours')
        )['total_hours'] or 0

        # Statystyki budżetów dla aktywnych zamówień
        active_orders_budgets = Order.objects.filter(
            user=user,
            status=Order.Status.ACTIVE
        ).aggregate(
            total_budget_capex=Sum('budget_capex'),
            total_budget_opex=Sum('budget_opex'),
            total_budget_consultation=Sum('budget_consultation')
        )

        # Wykorzystane godziny z rozliczeń miesięcznych
        used_hours = MonthlyReport.objects.filter(
            user=user,
            order__status=Order.Status.ACTIVE
        ).aggregate(
            used_capex=Sum('capex_hours'),
            used_opex=Sum('opex_hours'),
            used_consultation=Sum('consultation_hours')
        )

        # Wykorzystane godziny z nadgodzin
        overtime_hours = Overtime.objects.filter(
            user=user,
            order__status=Order.Status.ACTIVE,
            status='completed'
        ).aggregate(
            overtime_capex=Sum('hours', filter=models.Q(type='capex')),
            overtime_opex=Sum('hours', filter=models.Q(type='opex'))
        )

        # Obliczanie sumy wartości z aktywnych zamówień
        total_value = calculate_total_value(user)
        print(f"DEBUG: Całkowita wartość rozliczeń: {total_value} PLN")

        # Obliczanie pozostałych budżetów
        total_budget_capex = float(active_orders_budgets['total_budget_capex'] or 0)
        total_budget_opex = float(active_orders_budgets['total_budget_opex'] or 0)
        total_budget_consultation = float(active_orders_budgets['total_budget_consultation'] or 0)

        used_capex = float(used_hours['used_capex'] or 0)
        used_opex = float(used_hours['used_opex'] or 0)
        used_consultation = float(used_hours['used_consultation'] or 0)

        overtime_capex = float(overtime_hours['overtime_capex'] or 0)
        overtime_opex = float(overtime_hours['overtime_opex'] or 0)

        remaining_budget_capex = total_budget_capex - used_capex - overtime_capex
        remaining_budget_opex = total_budget_opex - used_opex - overtime_opex
        remaining_budget_consultation = total_budget_consultation - used_consultation

        # Obliczanie procentów wykorzystania dla każdego typu budżetu
        def calculate_percentage(used, total):
            if total and float(total) > 0:
                return (float(used) / float(total)) * 100
            return 0

        budget_percentages = {
            'capex': {
                'used': calculate_percentage(used_capex, total_budget_capex),
                'overtime': calculate_percentage(overtime_capex, total_budget_capex)
            },
            'opex': {
                'used': calculate_percentage(used_opex, total_budget_opex),
                'overtime': calculate_percentage(overtime_opex, total_budget_opex)
            },
            'consultation': {
                'used': calculate_percentage(used_consultation, total_budget_consultation),
                'overtime': 0  # Nie ma nadgodzin dla konsultacji
            }
        }

        # Nowa sekcja - Porównanie godzin między miesiącami
        # Pobieramy dane z poprzedniego miesiąca
        previous_month = end_date - timedelta(days=end_date.day)
        previous_month_start = previous_month.replace(day=1)
        previous_month_end = end_date.replace(day=1) - timedelta(days=1)

        # Pobieramy dane z bieżącego miesiąca
        current_month_start = end_date.replace(day=1)
        current_month_end = end_date

        # Statystyki dla poprzedniego miesiąca
        previous_month_stats = MonthlyReport.objects.filter(
            user=user,
            month__range=(previous_month_start, previous_month_end)
        ).aggregate(
            total_capex=Sum('capex_hours') or 0,
            total_opex=Sum('opex_hours') or 0,
            total_consultation=Sum('consultation_hours') or 0
        )

        # Statystyki dla bieżącego miesiąca
        current_month_stats = MonthlyReport.objects.filter(
            user=user,
            month__range=(current_month_start, current_month_end)
        ).aggregate(
            total_capex=Sum('capex_hours') or 0,
            total_opex=Sum('opex_hours') or 0,
            total_consultation=Sum('consultation_hours') or 0
        )

        # Dodajemy nadgodziny do statystyk
        previous_month_overtime = Overtime.objects.filter(
            user=user,
            start_time__range=(previous_month_start, previous_month_end),
            status='completed'
        ).aggregate(
            overtime_capex=Sum('hours', filter=models.Q(type='capex')) or 0,
            overtime_opex=Sum('hours', filter=models.Q(type='opex')) or 0
        )

        current_month_overtime = Overtime.objects.filter(
            user=user,
            start_time__range=(current_month_start, current_month_end),
            status='completed'
        ).aggregate(
            overtime_capex=Sum('hours', filter=models.Q(type='capex')) or 0,
            overtime_opex=Sum('hours', filter=models.Q(type='opex')) or 0
        )

        # Przygotowanie danych do porównania
        hours_comparison = {
            'previous_month': {
                'name': previous_month.strftime('%B %Y'),
                'capex': float(previous_month_stats['total_capex']) + float(previous_month_overtime['overtime_capex']),
                'opex': float(previous_month_stats['total_opex']) + float(previous_month_overtime['overtime_opex']),
                'consultation': float(previous_month_stats['total_consultation'])
            },
            'current_month': {
                'name': current_month_start.strftime('%B %Y'),
                'capex': float(current_month_stats['total_capex']) + float(current_month_overtime['overtime_capex']),
                'opex': float(current_month_stats['total_opex']) + float(current_month_overtime['overtime_opex']),
                'consultation': float(current_month_stats['total_consultation'])
            }
        }

        # Obliczanie procentowych zmian
        def calculate_change_percentage(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100

        hours_comparison['changes'] = {
            'capex': calculate_change_percentage(
                hours_comparison['current_month']['capex'],
                hours_comparison['previous_month']['capex']
            ),
            'opex': calculate_change_percentage(
                hours_comparison['current_month']['opex'],
                hours_comparison['previous_month']['opex']
            ),
            'consultation': calculate_change_percentage(
                hours_comparison['current_month']['consultation'],
                hours_comparison['previous_month']['consultation']
            )
        }

        context.update({
            'months': json.dumps(months),
            'capex_data': json.dumps(capex_data),
            'opex_data': json.dumps(opex_data),
            'consultation_data': json.dumps(consultation_data),
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'archived_orders': archived_orders,
            'recent_overtime': recent_overtime,
            'total_value': float(total_value),
            'budget_stats': {
                'capex': {
                    'total': total_budget_capex,
                    'used': used_capex,
                    'overtime': overtime_capex,
                    'remaining': remaining_budget_capex,
                    'percentages': budget_percentages['capex']
                },
                'opex': {
                    'total': total_budget_opex,
                    'used': used_opex,
                    'overtime': overtime_opex,
                    'remaining': remaining_budget_opex,
                    'percentages': budget_percentages['opex']
                },
                'consultation': {
                    'total': total_budget_consultation,
                    'used': used_consultation,
                    'overtime': 0,  # Nie ma nadgodzin konsultacyjnych
                    'remaining': remaining_budget_consultation,
                    'percentages': budget_percentages['consultation']
                }
            },
            'hours_comparison': hours_comparison  # Dodajemy nowe dane do kontekstu
        })

        return context
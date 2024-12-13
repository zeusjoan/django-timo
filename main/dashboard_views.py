from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from .models import Order, MonthlyReport, Overtime
import json
from datetime import datetime, timedelta
from django.utils import timezone

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

        context.update({
            'months': json.dumps(months),
            'capex_data': json.dumps(capex_data),
            'opex_data': json.dumps(opex_data),
            'consultation_data': json.dumps(consultation_data),
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'archived_orders': archived_orders,
            'recent_overtime': recent_overtime,
        })

        return context

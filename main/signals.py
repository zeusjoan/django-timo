from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderValue

@receiver(post_save, sender=Order)
def create_or_update_order_value(sender, instance, created, **kwargs):
    """
    Tworzy lub aktualizuje OrderValue przy zapisie zamówienia.
    """
    if instance.status == Order.Status.ACTIVE:
        # Pobierz lub utwórz OrderValue dla tego zamówienia
        order_value, _ = OrderValue.objects.get_or_create(order=instance)
        
        # Ustaw wartości początkowe z zamówienia
        order_value.capex_hours = instance.capex_hours
        order_value.opex_hours = instance.opex_hours
        order_value.consultation_hours = instance.consultation_hours
        
        # Oblicz wartość całkowitą
        order_value.calculate_total_value()
        order_value.save()
    else:
        # Jeśli zamówienie nie jest aktywne, usuń jego OrderValue jeśli istnieje
        OrderValue.objects.filter(order=instance).delete()

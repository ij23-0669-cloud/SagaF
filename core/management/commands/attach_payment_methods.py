from django.core.management.base import BaseCommand
from core.models import MetodoPagoUsuario, Usuario
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = 'Intenta adjuntar los PaymentMethods guardados a sus Stripe Customers (crea Customer si falta).'

    def handle(self, *args, **options):
        for m in MetodoPagoUsuario.objects.select_related('usuario').all():
            user = m.usuario
            try:
                if not user.stripe_customer_id:
                    customer = stripe.Customer.create(email=user.correo, name=f"{user.nombre} {user.apellido}", metadata={'usuario_id': user.id_usuario})
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    customer = stripe.Customer.retrieve(user.stripe_customer_id)

                pm = stripe.PaymentMethod.retrieve(m.stripe_payment_method_id)
                if getattr(pm, 'customer', None) == customer.id:
                    self.stdout.write(self.style.SUCCESS(f'OK: {m.id_metodo} ya adjunto a {customer.id}'))
                    continue
                if getattr(pm, 'customer', None) and pm.customer != customer.id:
                    self.stdout.write(self.style.WARNING(f'SKIP: {m.id_metodo} adjunto a otro customer {pm.customer}'))
                    continue
                stripe.PaymentMethod.attach(pm.id, customer=customer.id)
                self.stdout.write(self.style.SUCCESS(f'Attached {m.id_metodo} to {customer.id}'))
            except stripe.error.StripeError as e:
                self.stdout.write(self.style.ERROR(f'ERROR {m.id_metodo}: {str(e)}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR {m.id_metodo}: {str(e)}'))
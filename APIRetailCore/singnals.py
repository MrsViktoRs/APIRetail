from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal

from .models import ConfirmEmailToken, User

new_user_registered = Signal()
reset_password = Signal()
new_order = Signal()


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    """
    отправляем письмо с подтрердждением почты
    """
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Подтверждение регистрации пользователя {token.user.email}",
        # message:
        f'Перейдите по ссылке для подтверждения: http://127.0.0.1:8000/api/v1/account/activate/?token={token.key}',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )
    msg.send()


@receiver(reset_password)
def reset_password_signal(user_id, **kwargs):
    """
    отправляем письмо с подтрердждением почты
    """
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Смена пароля пользователя {token.user.email}",
        # message:
        f'Перейдите по ссылке для смены пароля: http://127.0.0.1:8000/api/v1/account/activate/?token={token.key}',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )
    msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    отправяем письмо при изменении статуса заказа
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Обновление статуса заказа",
        # message:
        'Заказ сформирован',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )
    msg.send()
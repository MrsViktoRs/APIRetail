from django.urls import path
from APIRetailCore.views import UpdateView, RegisterUserView, ConfirmAccountView

app_name = 'APIRetailCore'

urlpatterns = [
    path('update/', UpdateView.as_view()),
    path('register/', RegisterUserView.as_view()),
    path('account/activate/', ConfirmAccountView.as_view()),
]

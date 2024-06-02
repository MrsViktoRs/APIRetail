from django.urls import path
from APIRetailCore.views import RegisterUserView, ConfirmAccountView, PartnerUpdate, ControlAccountView, GetTokenView

app_name = 'APIRetailCore'

urlpatterns = [
    path('control/<int:pk>/', ControlAccountView.as_view({'get': 'retrieve', 'post': 'create', 'delete': 'destroy', 'put': 'update'})),
    path('update/', PartnerUpdate.as_view()),
    path('register/', RegisterUserView.as_view()),
    path('account/activate/', ConfirmAccountView.as_view()),
    path('get_token/', GetTokenView.as_view()),
]

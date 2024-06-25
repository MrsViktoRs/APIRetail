from django.urls import path
from APIRetailCore.views import RegisterUserView, ConfirmAccountView, PartnerUpdate, AccountDetails, LoginAccount, \
    ShopView, CategoryView, ProductView, ProductInfoV, BasketView, PartnerState, PartnerOrders, ContactView, \
    ResetPasswordView, ChangePasswordView, OrderView

app_name = 'APIRetailCore'

urlpatterns = [
    path('partner/update/', PartnerUpdate.as_view()),
    path('partner/state/', PartnerState.as_view()),
    path('partner/orders/', PartnerOrders.as_view()),
    path('register/', RegisterUserView.as_view()),
    path('account/activate/', ConfirmAccountView.as_view()),
    path('account/', AccountDetails.as_view()),
    path('account/login/', LoginAccount.as_view()),
    path('account/contact/', ContactView.as_view()),
    path('account/reset_password/', ResetPasswordView.as_view()),
    path('account/change_password/', ChangePasswordView.as_view()),
    path('shops/', ShopView.as_view()),
    path('categories/', CategoryView.as_view()),
    path('products/', ProductView.as_view()),
    path('product/info/<int:pk>/', ProductInfoV.as_view()),
    path('product/update/<int:pk>/', ProductInfoV.as_view()),
    path('product/delete/<int:pk>/', ProductInfoV.as_view()),
    path('basket/', BasketView.as_view()),
    path('order/', OrderView.as_view()),
    ]

import yaml
from django.contrib.auth import authenticate
from django.views import View
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from requests import get
from rest_framework.viewsets import ModelViewSet
from yaml import load as load_yaml, Loader

from APIRetailCore.models import *
from APIRetailCore.serializers import UserSerializer, ControllingViewSerializer
from APIRetailCore.mixins import RegisterValidation
from APIRetailCore.singnals import new_user_registered


class ControlAccountView(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ControllingViewSerializer
    action = {
        'get': 'retrieve',
        'put': 'update',
        'post': 'create',
        'delete': 'destroy',
    }


class RegisterUserView(APIView, RegisterValidation):
    def post(self, request, *args, **kwargs):
        try:
            self.validate_register(request.data)
            user_serializer = UserSerializer(data=request.data)
            if user_serializer.is_valid():
                user = user_serializer.save()
                user.set_password(request.data['password'])
                user.save()
                new_user_registered.send(sender=self.__class__, user_id=user.id)
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        except Exception as e:
            return JsonResponse({'status': False, 'errors': e.args})


class ConfirmAccountView(View):
    def get(self, request, *args, **kwargs):
        token = ConfirmEmailToken.objects.filter(key=request.GET['token']).first()
        if token:
            token.user.is_active = True
            new_token = Token.objects.create(user=token.user)
            token.user.save()
            token.delete()
            return HttpResponse(f'Ваш аккаунт подтвержден, ваш токен: {new_token.key}')
        else:
            return HttpResponse('Что-то пошло не так')


class GetTokenView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            if 'email' in request.data and 'password' in request.data:
                user = authenticate(email=request.data['email'], password=request.data['password'])
                if user:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
                else:
                    return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизоваться'})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Не указан email или пароль'})
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})


class PartnerUpdate(APIView):
    """Импорт товара из yaml файла"""

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        if request.FILES.get('file'):
            file = request.FILES.get('file')
            data = load_yaml(file, Loader=Loader)
        if request.data.get('url'):
            file = get(request.data.get('url')).content
            data = load_yaml(file, Loader=Loader)
        try:
            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data['goods']:
                product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item['id'],
                                                          model=item['model'],
                                                          price=item['price'],
                                                          price_rrc=item['price_rrc'],
                                                          quantity=item['quantity'],
                                                          shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)
            return JsonResponse({'data': True})
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})

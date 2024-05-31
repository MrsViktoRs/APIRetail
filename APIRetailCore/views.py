from django.views import View
from rest_framework.views import APIView
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from requests import get
from rest_framework.viewsets import ModelViewSet
from yaml import load as load_yaml, Loader

from APIRetailCore.models import *
from APIRetailCore.serializers import UserSerializer
from APIRetailCore.mixins import RegisterValidation
from APIRetailCore.singnals import new_user_registered


class ControlAccountView(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


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
            token.user.save()
            token.delete()
            return HttpResponse('Ваш аккаунт подтвержден')
        else:
            return HttpResponse('Что-то пошло не так')


class UpdateView(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

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

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
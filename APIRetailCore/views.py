from distutils.util import strtobool
from sqlite3 import IntegrityError
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.views import View
from django.db.models import Q, Sum, F
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from requests import get, Response
from rest_framework.viewsets import ModelViewSet
from yaml import load as load_yaml, Loader
from ujson import loads as load_json

from APIRetailCore.models import User, Category, Shop, Product, ProductInfo, ConfirmEmailToken, ProductParameter, \
    Parameter, Order, OrderItem, Contact
from APIRetailCore.serializers import UserSerializer, ControllingViewSerializer, CategorySerializer, ShopSerializer, \
    ProductSerializer, ProductInfoSerializer, OrderSerializer, OrderItemSerializer, ContactSerializer
from APIRetailCore.singnals import new_user_registered


class RegisterUserView(APIView):
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'status': False, 'password': error_array})
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            user.set_password(request.data['password'])
            user.save()
            new_user_registered.send(sender=self.__class__, user_id=user.id)
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


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


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    def post(self, request, *args, **kwargs):

        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            print(request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        serializer = UserSerializer(request.user)
        return JsonResponse(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for error in password_error:
                    error_array.append(error)
                return JsonResponse({'Status': False, 'Errors': error_array})
            else:
                request.user.set_password(request.data['password'])
        serializer = UserSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})


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
            return JsonResponse({'Status': True})
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductView(ListAPIView):
    """
    Класс для просмотра списка продуктов
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class ProductInfoV(APIView):
    def get(self, request, *args, **kwargs):
        try:
            product_info = ProductInfo.objects.filter(product_id=self.kwargs.get('pk'))
            product_info_serializer = ProductInfoSerializer(product_info, many=True)
            return JsonResponse(product_info_serializer.data, safe=False)
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})

    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        try:
            product_info = ProductInfo.objects.get(product_id=self.kwargs.get('pk'))
            data = request.data
            updated_fields = {field: data[field] for field in data if field != 'id'}
            for field, value in updated_fields.items():
                setattr(product_info, field, value)
            product_info.save()
            if updated_fields['parameter']:
                try:
                    parameter = Parameter.objects.get(name=updated_fields['parameter'])
                    product_parameter = ProductParameter.objects.get(product_info_id=product_info.id,
                                                                     parameter_id=parameter.id)
                    product_parameter.value = updated_fields['value']
                    product_parameter.save()
                except Parameter.DoesNotExist:
                    parameter = Parameter.objects.create(name=updated_fields['parameter'])
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter.id,
                                                    value=updated_fields['value'])
            return JsonResponse({'Status': True})
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})

    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        try:
            product_info = ProductInfo.objects.get(product_id=self.kwargs.get('pk'))
            product = Product.objects.get(name=product_info.product.name)
            product.delete()
            return JsonResponse({'Status': True})
        except Exception as e:
            return JsonResponse({'Status': False, 'Errors': e.args})


class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    # получить корзину
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(basket, many=True)
        return JsonResponse({'sattus': True, 'basket': serializer.data})

    # редактировать корзину
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            object_created = 0
            for item in items_sting:
                order_item = OrderItem.objects.get(order_id=basket.id, product_info_id=item['product_info'])
                order_item.quantity = item['quantity']
                order_item.save()
                object_created += 1
            return JsonResponse({'Status': True, 'Обновлено объектов': object_created})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        items_sting = request.data.get('items')
        if not items_sting:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
        objects_updated = 0
        basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
        for order_item in items_sting:
            order_object = OrderItem.objects.create(order_id=basket.id, product_info_id=order_item['product_info'],
                                              quantity=order_item['quantity'])
            order_object.save()
            if order_object:
                objects_updated += 1
        return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})


class PartnerState(APIView):
    """
    Класс для работы со статусом поставщика
    """

    # получить текущий статус
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return JsonResponse({'Status': True, 'state': serializer.data})

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return JsonResponse({'Status': True, 'orders': serializer.data})


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    # получить мои контакты
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return JsonResponse({'contacts':serializer.data})

    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать контакт
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                print(contact)
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
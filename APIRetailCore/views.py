from django.contrib.auth.password_validation import validate_password
from django.shortcuts import render
from rest_framework.views import APIView, Response
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from requests import get
from yaml import load as load_yaml, Loader

from APIRetailCore.serializers import UserSerializer


class RegisterUserView(APIView):

    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'status': 'ok'})


class UpdateView(APIView):

    def post(self, requests, *args, **kwargs):
        return JsonResponse({'status': 'ok'})
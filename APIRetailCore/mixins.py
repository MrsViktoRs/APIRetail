from django.contrib.auth.password_validation import validate_password


class RegisterValidation:
    """миксин для валидации входящих данных"""
    def validate_register(self, attrs):
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(attrs):
            try:
                validate_password(attrs['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return {'status': False, 'password': error_array}
        return {'password': 'Не указаны все необходимые аргументы'}
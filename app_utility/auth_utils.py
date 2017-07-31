import jwt
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status




class JWT_Verify():
    def __get__token(self, request = None):
        return request.META.get('HTTP_AUTHORIZATION') or request.GET.get('token')

    def process_request(self, request):
        token = self.__get__token(request)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY)
            request.user = User.objects.get(
                id = payload.get('id'),
                username = payload.get('username')
            )
        except jwt.ExpiredSignature:
            msg = {'Error': "Token is invalid"}
            return Response(msg, status=status.HTTP_403_FORBIDDEN)

        except jwt.DecodeError:
            msg = {'Error': "Token is invalid"}
            return Response(msg, status=status.HTTP_403_FORBIDDEN)

        except jwt.InvalidTokenError:
            msg = {'Error': "Token is invalid"}
            return Response(msg, status=status.HTTP_403_FORBIDDEN)

        except User.DoesNotExist:
            msg = {'Error': "User does not exist"}
            return Response(msg, status=status.HTTP_404_NOT_FOUND)



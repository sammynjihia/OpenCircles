# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth import authenticate,login,logout
from .serializers import MemberSerializer,PhoneNumberSerializer,ChangePasswordSerializer,AuthenticateUserSerializer
from rest_framework import viewsets
from member.models import Member
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
# from rest_framework.parsers import JSONParser
from app_utility import sms_utils,iprs_utils
from django.http import Http404
import random,datetime
import jwt
from datetime import datetime
from django.conf import settings


# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                         'register_member':reverse('member-registration',request=request,format=format),
                         'confirm_phone_number':reverse('confirm-number',request=request,format=format),
                         'change_password':reverse('change-password',request=request,format=format),
                         'login':reverse('login',request=request,format=format),
                         'logout':reverse('logout',request=request)
                    })

class MemberRegistration(APIView):
    """
        Registers new member
    """
    # parser_classes = (JSONParser,)
    def get_object(self,request):
        user_id = request.user.id
        obj = Member.objects.get(user_id=user_id)
        return obj

    def post(self,request,*args,**kwargs):
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            iprs = iprs_utils.Iprs()
            person_data = iprs.get_person_details(serializer.data.get('national_id'))
            print (person_data)
            member_info = { new_key : person_data.pop(key) for new_key,key in {'nationality':'citizenship','gender':'gender','date_of_birth':'dateOfBirth','passport_image_url':'photoPath'}.items()}
            user = authenticate(username=serializer.data.get('email'),password=request.data.get('pin'))
            login(request,user)
            self.object = self.get_object(request)
            for key,value in member_info.items():
                if key == "date_of_birth":
                    value = datetime.datetime.strptime(value,'%m/%d/%Y %I:%M:%S %p').date()
                elif key == "gender":
                    value = value.lower()
                    if value == "male":
                        value = "M"
                    else:
                        value = "F"
                setattr(self.object, key, value)
            self.object.save()
            data = { 'status':201,'member_object':serializer.data}
            return Response(data,status = status.HTTP_201_CREATED)
        else:
            data = {'status':400,'error':serializer.errors}
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

class LoginIn(APIView):
    """
    Authenticates user
    """
    def post(self,request,*args,**kwargs):
        serializer = AuthenticateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(username=serializer.data.get('username'),password=serializer.data.get('password'))

            if user:
                payload = {
                    'id': user.id,
                    'username':user.username,
                    'exp':datetime.now() + settings.EXPIRY_TIME
                }
                token = {'token':jwt.encode(payload, settings.SECRET_KEY)}
                login(request, user)
                return Response(token, status=status.HTTP_202_ACCEPTED)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logout(request):
    request.session.flush()
    data = {'status':200}
    return Response(data,status=status.HTTP_200_OK)

class ChangePassword(APIView):
    """
        Sets new password for member
    """
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        obj = self.request.user
        return obj

    def put(self,request,*args,**kwargs):
        self.object = self.get_object()
        serializer = ChangePasswordSerializer(data = request.data)
        if serializer.is_valid():
            old_password = serializer.data.get("old_password")
            #check old_password
            if not self.object.check_password(old_password):
                error = {'old_password':["Wrong password."]}
                data = {'status' : 400,'errors':error}
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            data = { 'status' : 200}
            return Response(data,status = status.HTTP_200_OK)
        else:
            data = {'status' : 400, 'errors':serializer.errors}
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

class PhoneNumberConfirmation(APIView):
    """
        Sends confirmation code to phone number
    """
    def post(self,request,format=None):
        serializer = PhoneNumberSerializer(data = request.data)
        if serializer.is_valid():
            sms = sms_utils.Sms()
            phone_number = serializer.data.get('phone_number')
            code = random.randint(1111,9999)
            message = 'Your confirmation code is {}.'.format(code)
            response = sms.sendsms(phone_number,message)
            if response:
                data = {'status':200,
                        'confirmation_code':code
                }
                return Response(data,status = status.HTTP_200_OK)
            else:
                data = {'status':400,
                         'message':'Unable to send confirmation code'
                }
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
        else:
            data = {'status': 400,
                     'errors':serializer.errors
            }
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

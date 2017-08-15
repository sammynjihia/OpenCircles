# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth import authenticate,login,logout
from django.http import Http404,HttpResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token

from app_utility import sms_utils,iprs_utils
from .serializers import MemberSerializer,PhoneNumberSerializer,ChangePasswordSerializer,AuthenticateUserSerializer
from member.models import Member

import random,datetime,json

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
        Registers new member,requires first_name,last_name,email,pin,phone_number and national_id to be provided
    """

    def post(self,request,*args,**kwargs):
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            iprs = iprs_utils.Iprs()
            person_data = iprs.get_person_details(serializer.data.get('national_id'))
            if type(person_data) is dict:
                app_data = { key : serializer.data.get(key) for key in ['first_name','last_name']}
                valid,response = iprs.validate_info(person_data,app_data)
                if valid:
                    new_member = serializer.save()
                    token = Token.objects.create(user=new_member.user)
                    iprs.save_extracted_iprs_info(new_member,person_data)
                    new_member.is_validated = True
                    new_member.save()
                    login(request,new_member.user)
                    data = { 'status':201,'token':token.key }
                    status = status.HTTP_201_CREATED
                else:
                    data = { 'status':404,'errors':response}
                    status = status.HTTP_400_BAD_REQUEST
            else:
                new_member = serializer.save()
                token = Token.objects.create(user=new_member.user)
                error = {"IPRS_SERVER":["Currently unavailable"]}
                data = {'status':503,'errors': error}
                status = status.HTTP_503_SERVICE_UNAVAILABLE

            return Response(data,status = status)
        else:
            data = {'status':400,'error':serializer.errors}
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def test_data(request):
    print(request.POST)
    return_data = {
        'status': 1,
        'token': "klhft8734tgekgfspdj02q34324",
        'message': ""
    }
    return HttpResponse(json.dumps(return_data))

class LoginIn(APIView):
    """
    Authenticates user,requires username and password to be provided
    """
    def post(self,request,*args,**kwargs):
        print request.data
        serializer = AuthenticateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(username=serializer.data.get('username'),password=serializer.data.get('pin'))
            if user is not None:
                if user.member.is_validated:
                    login(request,user)
                    token = Token.objects.filter(user=user)
                    if not token:
                        token = Token.objects.create(user=user)
                    data = {'status':1,'token':token.key }

                    return Response(data,status=status.HTTP_200_OK)
            data={"status":0,"message":"Invalid credentials"}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
        data={"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logout(request):
    token = Token.objects.get(user=request.user)
    request.session.flush()
    token.delete()
    data = {'status':200}
    return Response(data,status=status.HTTP_200_OK)

class ChangePassword(APIView):
    """
        Sets new password for member,requires old_password and new_password to be provided
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
        Sends confirmation code to phone number,requires phone_number to be provided
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

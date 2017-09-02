# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth import authenticate,login,logout
from django.http import Http404,HttpResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token

from app_utility import sms_utils,iprs_utils,accounts_utils
from .serializers import MemberSerializer,PhoneNumberSerializer,ChangePasswordSerializer,AuthenticateUserSerializer
from member import serializers

from member.models import Member
from wallet.models import Wallet

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
    @csrf_exempt
    def post(self,request,*args,**kwargs):
        if 'contact_list' in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data['contact_list'] = json.loads(request.data['contact_list'])
            contacts = request.data['contact_list'] if 'contact_list' in request.data else []
            request.data._mutable = mutable
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            instance = accounts_utils.Account()
            if serializer.validated_data['country'].lower() == 'kenya':
                iprs = iprs_utils.Iprs()
                person_data = iprs.get_person_details(serializer.validated_data.get('national_id'))
                if type(person_data) is dict:
                    app_data = { key : serializer.validated_data['user'].get(key) for key in ['first_name','last_name']}
                    valid,response = iprs.validate_info(person_data,app_data)
                    if valid:
                        new_member = serializer.save()
                        iprs.save_extracted_iprs_info(new_member,person_data)
                    else:
                        data = { 'status':0,'message':response}
                        return Response(data,status = status.HTTP_400_BAD_REQUEST)
                else:
                    new_member = serializer.save()
                    token = Token.objects.create(user=new_member.user)
                    Wallet.objects.create(member=new_member,acc_no=new_member.national_id)
                    instance.save_contacts(new_member,contacts)
                    error = {"IPRS_SERVER":["Currently unavailable"]}
                    data = {'status':0,'message': error}
                    return Response(data,status = status.HTTP_503_SERVICE_UNAVAILABLE)

            else:
                new_member = serializer.save()
            token = Token.objects.create(user=new_member.user)
            new_member.is_validated = True
            new_member.save()
            login(request,new_member.user)
            Wallet.objects.create(member=new_member,acc_no=new_member.national_id)
            instance.save_contacts(new_member,contacts)

            data = { 'status':1,'token':token.key }
            return Response(data,status = status.HTTP_201_CREATED)
        else:
            print serializer.errors
            data = {'status':0,'message':'asdf'}
            print data
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def test_data(request):
    return_data = {
        'status': 1,
        'token': "klhft8734tgekgfspdj02q34324",
        'message': ""
    }
    return HttpResponse(json.dumps(return_data))

class LoginIn(APIView):
    """
    Authenticates user,requires username and pin to be provided
    """
    def post(self,request,*args,**kwargs):
        serializer = AuthenticateUserSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            if User.objects.filter(email=username).exists():
                username=User.objects.get(email=username).username
            else:
                username = sms_utils.Sms().format_phone_number(username)
            user = authenticate(username=username,password=serializer.data.get('pin'))
            if user is not None:
                if user.member.is_validated:
                    login(request,user)
                    try:
                        token = Token.objects.get(user=user)
                    except Token.DoesNotExist:
                        token = Token.objects.create(user=user)
                    serializer = serializers.MemberSerializer(request.user.member)
                    data = {'status':1,'token':token.key,'member':serializer.data }
                    return Response(data,status=status.HTTP_200_OK)
            data={"status":0,"message":"Invalid credentials"}
            print data
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
        data={"status":0,"message":serializer.errors}
        print data
        return Response(data,status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    token = Token.objects.get(user=request.user)
    request.session.flush()
    token.delete()
    data = {'status':1}
    return Response(data,status=status.HTTP_200_OK)

class ChangePassword(APIView):
    """
        Sets new password for member,requires old_password and new_password to be provided
    """
    authentication_classes = (TokenAuthentication,)
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
            phone_number = serializer.data.get('phone')
            code = random.randint(1111,9999)
            message = 'Your confirmation code is {}'.format(code)
            response = sms.sendsms(phone_number,message)
            if response:
                data = {'status':1,
                        'confirmation_code':code
                }
                return Response(data,status = status.HTTP_200_OK)
            else:
                data = {'status':0,
                         'message':'Unable to send confirmation code'
                }
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
        else:
            data = {'status': 0,
                     'message':serializer.errors
            }
            return Response(data,status = status.HTTP_400_BAD_REQUEST)

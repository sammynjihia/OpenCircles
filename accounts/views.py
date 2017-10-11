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

from app_utility import sms_utils,iprs_utils,accounts_utils,general_utils
from .serializers import *
from member.serializers import MemberSerializer

from member.models import Member
from wallet.models import Wallet

import random,datetime,json
from accounts import tasks


class MemberRegistration(APIView):
    """
        Registers new member,requires first_name,last_name,email,pin,phone_number and national_id to be provided
    """
    @csrf_exempt
    def post(self,request,*args,**kwargs):
        if "contact_list" in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data["contact_list"] = json.loads(request.data['contact_list'])
            contacts = request.data["contact_list"] if "contact_list" in request.data else []
            request.data._mutable = mutable
        serializer = MemberRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            created_objects = []
            instance = accounts_utils.Account()
            if serializer.validated_data["country"].lower() == "kenya":
                iprs = iprs_utils.Iprs()
                # person_data = iprs.get_person_details(serializer.validated_data.get("national_id"))
                person_data = {}
                if type(person_data) is dict:
                    # app_data = { key : serializer.validated_data['user'].get(key) for key in ['first_name','last_name']}
                    # valid,response = iprs.validate_info(person_data,app_data)
                    valid = True
                    if valid:
                        new_member = serializer.save()
                        # iprs.save_extracted_iprs_info(new_member,person_data)
                    else:
                        data = { 'status':0,'message':response}
                        return Response(data,status = status.HTTP_200_OK)
                # IPRS server down
                else:
                    try:
                        new_member = serializer.save()
                        created_objects.append(new_member.user)
                        token = Token.objects.create(user=new_member.user)
                        wallet = Wallet.objects.create(member=new_member,acc_no=new_member.national_id)
                        #instance.save_contacts(new_member,contacts)
                        contact_save = tasks.save_member_contacts(new_member,contacts)
                        contact_save.delay()


                    except Exception as e:
                        print(str(e))
                        instance = general_utils.General()
                        instance.delete_created_objects(created_objects)
                        data = {"status":0,"message": "Unable to register"}
                        return Response(data,status = status.HTTP_200_OK)
                    data = {"status":0,"message": "Server is currently unavailable"}
                    return Response(data,status = status.HTTP_200_OK)
            else:
                new_member = serializer.save()
            created_objects.append(new_member.user)
            try:
                token = Token.objects.create(user=new_member.user)
                new_member.is_validated = True
                new_member.save()
                Wallet.objects.create(member=new_member,acc_no=new_member.national_id)
                print("hapa")
                #instance.save_contacts(new_member,contacts)
                contact_save = tasks.save_member_contacts(new_member, contacts)
                contact_save.delay()
                login(request,new_member.user)
            except Exception as e:
                print(str(e))
                instance = general_utils.General()
                instance.delete_created_objects(created_objects)
                data = {"status":0,"message": "Unable to register"}
                return Response(data,status = status.HTTP_200_OK)
            data = { "status":1,"token":token.key }
            return Response(data,status = status.HTTP_201_CREATED)

        data = {"status":0,"message":serializer.errors}
        return Response(data,status = status.HTTP_200_OK)

class LoginIn(APIView):
    """
    Authenticates user,requires username and pin to be provided
    """
    def post(self,request,*args,**kwargs):
        serializer = AuthenticateUserSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get("username")
            if User.objects.filter(email=username).exists():
                username=User.objects.get(email=username).username
            else:
                username = sms_utils.Sms().format_phone_number(username)
            user = authenticate(username=username,password=serializer.validated_data.get("pin"))
            if user is not None:
                if user.member.is_validated:
                    login(request,user)
                    user.member.device_token = serializer.validated_data['app_token']
                    user.member.save()
                    token,created = Token.objects.get_or_create(user=user)
                    serializer = MemberSerializer(request.user.member)
                    data = {"status":1,"token":token.key,"member":serializer.data }
                    return Response(data,status=status.HTTP_200_OK)
            data={"status":0,"message":"Invalid credentials"}
            return Response(data,status=status.HTTP_200_OK)
        data={"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    token = Token.objects.get(user=request.user)
    member = request.user.member
    member.device_token = ''
    member.save()
    request.session.flush()
    token.delete()
    data = {'status':1}
    return Response(data,status=status.HTTP_200_OK)

class ChangePassword(APIView):
    """
        Sets new pin for member,requires old_pin and new_pin to be provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        self.object = request.user
        serializer = ChangePasswordSerializer(data = request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get("old_pin")
            #check old_password
            if not self.object.check_password(old_password):
                error = "Incorrect pin provided"
                data = {'status' :0,'message':error}
                return Response(data,status=status.HTTP_200_OK)
            self.object.set_password(serializer.validated_data.get("new_pin"))
            self.object.save()
            data = { "status":1,"message":"You have successfully changed your pin"}
            return Response(data,status = status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data,status = status.HTTP_200_OK)

class PhoneNumberConfirmation(APIView):
    """
        Sends confirmation code to phone number,requires phone_number to be provided
    """
    def post(self,request,*args,**kwargs):
        mutable = request.data._mutable
        request.data._mutable = True
        instance = sms_utils.Sms()
        request.data["phone"] = instance.format_phone_number(request.data["phone"])
        request.data._mutable = mutable
        print(request.data)
        serializer = PhoneNumberSerializer(data = request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data.get("phone_number")
            code = random.randint(1111,9999)
            message = "Your confirmation code is {}".format(code)
            response = instance.sendsms(phone_number,message)
            if response:
                data = {"status":1,"confirmation_code":code}
                return Response(data,status = status.HTTP_200_OK)
            data = {"status":0,"message":"Unable to send confirmation code"}
            return Response(data,status=status.HTTP_200_OK)
        error = "".join(serializer.errors['phone'])
        data = {"status": 0,"message":error}
        return Response(data,status = status.HTTP_200_OK)

class UpdateDeviceToken(APIView):
    """
    Updates device registration token
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = RegistrationTokenSerializer(data=request.data)
        if serializer.is_valid():
            member,token = request.user.member,serializer.validated_data('app_token')
            member.device_token(token)
            member.save()
            data = {"status":1}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
def send_short_code(request,*args,**kwargs):
    serializer = PhoneSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        instance = sms_utils.Sms()
        code = random.randint(11111,99999)
        message = "Pin reset short code is {}".format(code)
        response = instance.sendsms(phone_number,message)
        if response:
            data = {"status":1,"short_code":code}
            return Response(data,status = status.HTTP_200_OK)
        data = {"status":0,"message":"Unable to send pin rest short code"}
        return Response(data,status=status.HTTP_200_OK)
    data = {"status":0,"message":serializer.errors}
    return Response(data,status=status.HTTP_200_OK)


class ResetPin(APIView):
    """
    Reset user's password
    """
    def post(self,request,*args,**kwargs):
        serializer = ResetPinSerializer(data=request.data)
        if serializer.is_valid():
            try:
                try:
                    phone_number = sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number'])
                    member = Member.objects.get(phone_number=phone_number)
                except Member.DoesNotExist:
                    data = {"status":0,"message":"Unable to reset pin.User is not a member."}
                    return Response(data,status=status.HTTP_200_OK)
                user = member.user
                user.set_password(serializer.validated_data['pin'])
                user.save()
                data = {"status":1,"message":"Successful pin reset."}
                return Response(data,status=status.HTTP_200_OK)
            except Exception as e:
                print(str(e))
                data = {"status":0,"message":"Unable to reset pin"}
                return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

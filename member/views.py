from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import Http404

from rest_framework.decorators import detail_route
from rest_framework.views import APIView
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework import viewsets
from rest_framework.parsers import FileUploadParser,FormParser

from .serializers import MemberSerializer,BeneficiarySerializer,MemberBeneficiarySerializer,NewContactSerializer
from member.models import Member,Beneficiary,Contacts
from app_utility import sms_utils,member_utils,accounts_utils,general_utils
from accounts.serializers import PhoneNumberSerializer

import random

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                        'member_detail':reverse('member-detail',request=request,format=format)
                   })

class MemberDetail(APIView):
    """
    retrives specific member details
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def get_object(self,phone_number):
        try:
            return Member.objects.get(phone_number=phone_number)
        except Member.DoesNotExist:
            raise Http404

    def post(self,request,*args,**kwargs):
        serializer = PhoneNumberSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number'])
            # phone_number = serializer.validated_data['phone_number']
            member = self.get_object(phone_number)
            member_serializer = MemberSerializer(member,context={'request':request})
            data = {"status":1,"member":member_serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)


class BeneficiaryRegistration(APIView):
    """
    Registers a new beneficiary
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = BeneficiarySerializer(data=request.data)
        if serializer.is_valid():
            if request.user.check_password(serializer.validated_data['pin']):
                instance = member_utils.OpenCircleMember()
                assigned_benefit = serializer.validated_data['benefit']
                if assigned_benefit > 100:
                    message = "Unable to add the new beneficiary.Maximum allowed benefit is 100%"
                    data = {"status":0,"message":message}
                    return Response(data,status=status.HTTP_200_OK)
                benefit = instance.calculate_member_benefit(request.user.member)
                if benefit == 100:
                    message = "Unable to add the new beneficiary.Your total benefits has reached the 100% limit."
                    data = {"status":0,"message":message}
                    return Response(data,status=status.HTTP_200_OK)
                total_benefit = benefit + assigned_benefit
                if total_benefit <= 100:
                    beneficiary = serializer.save(member=request.user.member)
                    message = "{} {} was added as your beneficiary with {}%  benefit".format(beneficiary.first_name,beneficiary.last_name,beneficiary.benefit*100)
                    data = {"status":1,"message":message}
                    return Response(data,status=status.HTTP_200_OK)
                allowed_benefit = 100-benefit
                message = "Unable to add the new beneficiary.Your maximum allowed benefit is {}%.".format(allowed_benefit)
                data = {"status":0,"message":message}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":"Incorrect pin"}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class MemberBeneficiary(APIView):
    """
    Fetches all members beneficiaries
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        beneficiaries = Beneficiary.objects.filter(member=request.user.member)
        member_serializer = MemberBeneficiarySerializer(beneficiaries,many=True)
        data = {"status":1,"beneficiaries":member_serializer.data}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def save_new_contact(request):
    serializer = NewContactSerializer(data=request.data)
    if serializer.is_valid():
        contact = serializer.validated_data['contacts']
        sms_instance, account_instance, member_instance = sms_utils.Sms(), accounts_utils.Account(), member_utils.OpenCircleMember()
        contact = account_instance.format_contacts(contact, sms_instance)
        created_objects = []
        try:
            new_contact,created = Contacts.objects.get_or_create(phone_number=contact['phone'], is_member=member_instance.get_is_member(contact['phone']), name=contact['name'], member=request.user.member, is_valid=contact['is_valid'])
            if created:
                created_objects.append(new_contact)
            data = {"status":1}
        except Exception as e:
            print(str(e))
            general_utils.General().delete_created_objects(created_objects)
            data = {"status":0}
        return Response(data,status=status.HTTP_200_OK)
    data = {"status":0,"message":serializer.errors}
    return Response(data,status=status.HTTP_200_OK)

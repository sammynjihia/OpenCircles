from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import Http404

from rest_framework.decorators import detail_route
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework import viewsets
from rest_framework.parsers import FileUploadParser,FormParser

from .serializers import MemberSerializer,BeneficiarySerializer
from member.models import Member,Beneficiary
from app_utility import sms_utils
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
            # phone_number = sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number'])
            phone_number = serializer.validated_data['phone_number']
            member = self.get_object(phone_number)
            serializer = MemberSerializer(member,context={'request':request})
            data = {'status':1,'member':serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {'status':0,'message':serializer.errors}
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
                serializer.save(member=request.user.member)
                data = {"status":1}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":1,"message":"Incorrect pin"}
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
        serializer = MemberSerializer(beneficiaries,many=True)
        data = {"status":1,"beneficiaries":serializer.data}
        return Response(data,status=status.HTTP_200_OK)

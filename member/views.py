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

from .serializers import MemberSerializer
from member.models import Member
from app_utility import sms_utils
from accounts.serializers import PhoneNumberSerializer

import random

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                        'member_detail':reverse('member-detail',request=request,format=format)
                   })

# class MemberViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     Lists and retrieves member
#     """
#     queryset = Member.objects.all()
#     serializer_class = MemberSerializer


# class MemberList(APIView):
#     """
#     List all members
#     """
#     def get(self,request,*args,**kwargs):
#         members = Member.objects.all()
#         serializer = MemberSerializer(members,many=True,context={'request': request})
#         data = {'status':200,'members':serializer.data}
#         return Response(data,status=status.HTTP_200_OK)
#
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
            print phone_number
            member = self.get_object(phone_number)
            serializer = MemberSerializer(member,context={'request':request})
            data = {'status':1,'member':serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {'status':0,'message':serializer.errors}
        print data
        return Response(data,status=status.HTTP_400_BAD_REQUEST)


# class MemberViewSet(viewsets.ModelViewSet):
#     queryset = Member.objects.all()
#     serializer_class = MemberSerializer
#
#     @detail_route(methods=['put'])
#     def put(self, request, *args, **kwargs):
#         kwargs['partial'] = True
#         return self.update(request, *args, **kwargs)

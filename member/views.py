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
from rest_framework import viewsets

from .serializers import MemberSerializer
from member.models import Member
from app_utility import sms_utils

import random

# Create your views here.
# @api_view(['GET'])
# def api_root(request,format=None):
#     return Response({
#                         'member_list':reverse('member-list',request=request,format=format)
#                    })

class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lists and retrieves member
    """
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

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
# class MemberDetail(APIView):
#     """
#     retrives specific member details
#     """
#     def get_object(self,pk):
#         try:
#             return Member.objects.get(pk=pk)
#         except Member.DoesNotExist:
#             raise Http404
#
#     def get(self,request,*args,**kwargs):
#         member = self.get_object(kwargs['pk'])
#         serializer = MemberSerializer(member,context={'request':request})
#         data = {'status':200,'member':serializer.data}
#         return Response(data)


# class MemberViewSet(viewsets.ModelViewSet):
#     queryset = Member.objects.all()
#     serializer_class = MemberSerializer
#
#     @detail_route(methods=['put'])
#     def put(self, request, *args, **kwargs):
#         kwargs['partial'] = True
#         return self.update(request, *args, **kwargs)

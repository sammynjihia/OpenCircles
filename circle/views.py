from django.shortcuts import render
from django.http import Http404

from .models import Circle,CircleMember,CircleInvitation
from .serializers import *

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                       'circle creation':reverse('circle-create',request=request,format=format),
                       'circle list' : reverse('circle-list',request=request,format=format),
                       'circle-invitation-response' : reverse('circle-invitation-response',request=request,format=format)
    })
class CircleCreation(APIView):
    """
    Creates new circle when circle_name,circle_type and contact_list(should be a list/array datatype) are provided
    """
    permission_classes=(IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        request.data['circle_name'] = request.data.get('circle_name').lower()
        serializer = CircleCreationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                last_circle_created = Circle.objects.last()
                if last_circle_created:
                    last_acc_number = int(last_circle_created.circle_acc_number)
                    acc_number = last_acc_number + 1
                else:
                    acc_number = 100000
                acc_number = str(acc_number)
                circle = serializer.save(initiated_by=request.user.member,circle_acc_number=acc_number)
                member = request.user.member
                circle_member = CircleMember.objects.create(member=member,circle=circle)
                contact_list = request.data.get('contact_list')

                if len(contact_list):
                    for phone_number in contact_list:
                        CircleInvitation.objects.create(invited_by=circle_member,phone_number=phone_number)
                return Response(serializer.data,status = status.HTTP_201_CREATED)
            except Exception,e:
                print str(e)
                raise Exception
        return Response(serializer.errors)

class CircleList(APIView):
    """
    Lists all circles/retrieves specific circle by appending circle id to the url
    """
    authentication_classes = (TokenAuthentication,)
    def get_object(self,pk):
        try:
            return Circle.objects.get(pk=pk)
        except Circle.DoesNotExist:
            raise Http404

    def get(self,request,*args,**kwargs):
        if len(kwargs):
            circle = self.get_object(kwargs.get('pk'))
            serializer = CircleSerializer(circle,context={'request':request})
        else:
            circle = Circle.objects.all()
            serializer = CircleSerializer(circle,many=True,context={'request':request})
        return Response(serializer.data,status = status.HTTP_200_OK)

class CircleInvitationResponse(APIView):
    """
    Recieves circle invitation response,invite_id and invite_response are to be provided
    """
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = CircleInvitationSerializer(data=request.data)
        if serializer.is_valid():
            pk = int(serializer.data.get('invite_id'))
            response = serializer.data.get('invite_response')
            circle_invite = CircleInvitation.objects.get(pk=pk)
            if response is 'D':
                circle_invite.delete()
                return Response(status=status.HTTP_200_OK)
            else:
                circle = Circle.objects.get(id = circle_invite.invited_by.circle_id)
                circle_member = CircleMember.objects.create(circle=circle,member=request.user.member)
                if not circle.is_active:
                    count = CircleMember.objects.filter(circle_id=circle.id).count()
                    if count >= 5:
                        circle.save(is_active=True)
                serializer = CircleSerializer(circle,context={"request":request})
                return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors)

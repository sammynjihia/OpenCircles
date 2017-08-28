from django.shortcuts import render
from django.http import Http404
from django.db.models import Q
from django.contrib.auth import login

from .models import Circle,CircleMember,CircleInvitation,AllowedGuarantorRequest
from member.models import Contacts,Member
from .serializers import *

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication,BasicAuthentication
from rest_framework.authtoken.models import Token
from django.utils.six import text_type

from app_utility import circle_utils

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                       'circle creation':reverse('circle-create',request=request,format=format),
                       'circle list' : reverse('circle-list',request=request,format=format),
                       'join circle': reverse('join-circle',request=request,format=format),
                       'circle-invitation-response' : reverse('circle-invitation-response',request=request,format=format)
    })
class CircleCreation(APIView):
    """
    Creates new circle when circle_name,circle_type and contact_list(should be a list/array datatype) are provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
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
                    circle_invites = [CircleInvitation(invited_by=circle_member,phone_number=phone) for phone in phone_number]
                    CircleInvitation.objects.bulk_create(circle_invites)
                data = {"status":1}
                return Response(data,status = status.HTTP_201_CREATED)
            except Exception,e:
                print str(e)
                data = {"status":0}
                return Response(data,status = status.HTTP_400_BAD_REQUEST)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status = status.HTTP_400_BAD_REQUEST)

class CircleList(APIView):
    """
    Lists all circles/retrieves specific circle by appending circle id to the url
    """
    permission_classes = (IsAuthenticated,)
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
            print request.user
            serializer = CircleSerializer(circle,many=True,context={'request':request})
        return Response(serializer.data,status = status.HTTP_200_OK)

class MemberCircle(APIView):
    """
    Lists member's circles and suggested circles
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = TokenSerializer(data=request.data)
        if serializer.is_valid():
            instance = circle_utils.Circle()
            circles_ids = list(CircleMember.objects.filter(member=request.user.member).values_list('circle',flat=True))
            unjoined_cirles = Circle.objects.filter(~Q(id__in=circles_ids),circle_type="OPEN")
            contacts = Contacts.objects.filter(member=request.user.member,is_member=True).values_list('phone_number',flat=True)
            suggested_circles = instance.get_suggested_circles(unjoined_cirles,contacts)
            suggested_circles_ids = [key.id for key,value in suggested_circles] + circles_ids
            circles = Circle.objects.filter(id__in=suggested_circles_ids)
            serializer = CircleSerializer(circles,many=True,context={'request':request})
            data={"status":1,"circles":serializer.data}
            return Response(data,status = status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)



class CircleInvitationResponse(APIView):
    """
    Recieves circle invitation response,invite_id and invite_response are to be provided
    """
    authentication_classes = (TokenAuthentication,)
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

class AllowedGuarantorRequestSetting(APIView):
    """
    Serializer for setting and retrieving list of guarantors member can receive request,on post provide guarantor_list
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def get_object(self,request,*args):
        try:
            return AllowedGuarantorRequest.object.get(allows_request_from=allowed_request,circle_member=user)
        except AllowedGuarantorRequest.DoesNotExist:
            raise Http404

    def post(self,request,*args,**kwargs):
        serializer = AllowedGuarantorRequestSerializer(data=request.data)
        circle_name = kwargs['circlename']
        if serializer.is_valid():
            circle,guarantor_list = Circle.objects.get(circle_name=circle_name),serializer.validated_data['guarantor_list']
            circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
            member_ids = Member.objects.filter(Q(national_id__in=guarantor_list)|Q(phone_number__in=guarantor_list)).values_list('id',flat=True)
            acceptable_guarantor_requests = CircleMember.objects.filter(circle=circle,member_id__in = member_ids)
            allowed_guarantor_objs = [AllowedGuarantorRequest(circle_member=circle_member,allows_request_from=member) for member in acceptable_guarantor_requests ]
            AllowedGuarantorRequest.objects.bulk_create(allowed_guarantor_objs)
            data = {"status":1}
            return Response(data,status=status.HTTP_201_CREATED)
        data = {"status":0,"errors":serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)

    def get(self,request,*args,**kwargs):
        circle_name = kwargs['circlename']
        circle_member = CircleMember.objects.get(circle=Circle.objects.get(circle_name=circle_name),member=request.user.member)
        serializer = AllowedGurantorSerializer(circle_member,context={"request":request})
        data = {"status":1,"message":serializer.data}
        return Response(data,status=status.HTTP_200_OK)

class JoinCircle(APIView):
    """
    Adds member to circle
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = JoinCircleSerializer(data=request.data)
        if serializer.is_valid():
            acc_number,amount,pin = serializer.validated_data['circle_acc_number'],serializer.validated_data['amount'],serializer.validated_data['pin']
            circle = Circle.objects.get(circle_acc_number=acc_number)
            try:
                instance = circle_utils.Circle()
                circle_member = CircleMember.objects.create(circle=circle,member=request.user.member)
                instance.check_update_circle_status(circle)
                data,return_status = {"status":1},status.HTTP_200_OK
            except Exception,e:
                print str(e)
                data,return_status = {"status":0,"message":"Unable to add member"},status.HTTP_400_BAD_REQUEST
            return Response(data,status=return_status)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_objs(request,*args,**kwargs):
    circle,member = Circle.objects.get(circle_name=kwargs['circlename']),Member.objects.get(phone_number=kwargs['phonenumber'])
    try:
        allowed_request = CircleMember.objects.get(circle=circle,member=member)
        user = CircleMember.objects.get(circle=circle,member=request.user.member)
    except CircleMember.DoesNotExist:
        raise Http404
    agrs = AllowedGuarantorRequestSetting()
    obj = agrs.get_object(allowed_request,user)
    return Response(status=status.HTTP_200_OK)

from django.shortcuts import render
from django.http import Http404
from django.db.models import Q
from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist

from .models import Circle,CircleMember,CircleInvitation,AllowedGuarantorRequest
from member.models import Contacts,Member
from shares.models import Shares,IntraCircleShareTransaction
from .serializers import *

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication,BasicAuthentication
from rest_framework.authtoken.models import Token

from app_utility import circle_utils,wallet_utils,sms_utils

import datetime,json

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
        # request.data['circle_name'] = request.data.get('circle_name').lower()
        if 'contact_list' in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data['contact_list'] = json.loads(request.data['contact_list'])
            contacts = request.data['contact_list'] if 'contact_list' in request.data else []
            request.data._mutable = mutable
        serializer = CircleCreationSerializer(data=request.data)
        if serializer.is_valid():
            created_objects=[]
            try:
                last_circle_created = Circle.objects.last()
                if last_circle_created:
                    last_acc_number = int(last_circle_created.circle_acc_number)
                    acc_number = last_acc_number + 1
                else:
                    acc_number = 100000
                member = request.user.member
                circle = serializer.save(initiated_by=member,circle_acc_number=acc_number)
                created_objects.append(circle)
                circle_member = CircleMember.objects.create(member=member,circle=circle)
                created_objects.append(circle_member)
                shares = Shares.objects.create(circle_member=circle_member)
                created_objects.append(shares)
                if len(contacts):
                    instance = sms_utils.Sms()
                    circle_invites = [CircleInvitation(invited_by=circle_member,phone_number=phone) for phone in contacts]
                    invites = CircleInvitation.objects.bulk_create(circle_invites)
                    created_objects.append(invites)
                serializer = CircleSerializer(circle,context={'request':request})
                data={"status":1,"circle":serializer.data}
                return Response(data,status=status.HTTP_201_CREATED)
            except Exception,e:
                print(str(e))
                for obj in created_objects:
                    if type(obj) is list:
                        for ob in obj:
                            ob.delete()
                    else:
                        obj.delete()
                error = "Unable to create circle"
                data = {"status":0,"message":error}
                return Response(data,status = status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status = status.HTTP_200_OK)

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
            unjoined_circles = Circle.objects.filter(~Q(id__in=circles_ids))
            contacts = Contacts.objects.filter(member=request.user.member,is_member=True).values_list('phone_number',flat=True)
            suggested_circles = instance.get_suggested_circles(unjoined_circles,contacts)
            invited_circles = instance.get_invited_circles(request,unjoined_circles)
            invited_circles_ids  = [circle.id for circle in invited_circles]
            suggested_circles_ids = list(set([key.id for key,value in suggested_circles] + circles_ids + invited_circles))
            circles = Circle.objects.filter(id__in=suggested_circles_ids)
            serializer = CircleSerializer(circles,many=True,context={'request':request})
            data={"status":1,"circles":serializer.data}
            return Response(data,status = status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

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
            return Response(serializer.errors,status=status.HTTP_200_OK)

class AllowedGuaranteeRegistration(APIView):
    """
    Adds guarantees
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        print request.data
        serializer = AllowedGuaranteeSerializer(data=request.data)
        if serializer.is_valid():
            instance = sms_utils.Sms()
            circle,guarantee_phone = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number']),instance.format_phone_number(serializer.validated_data['guarantee'])
            if guarantee_phone == request.user.member.phone_number:
                data = {"status":0,"message":"Unable to add yourself to guarantee reuest list"}
                return Response(data,status=status.HTTP_200_OK)
            user_circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
            guarantee_member = Member.objects.get(phone_number=guarantee_phone)
            allowed_guarantee = CircleMember.objects.get(circle=circle,member = guarantee_member)
            try:
                AllowedGuarantorRequest.objects.create(circle_member=user_circle_member,allows_request_from=allowed_guarantee)
            except Exception as e:
                print (str(e))
                ms = "Unable to add {} {} to guarantee request list".format(guarantee_member.user.first_name,guarantee_member.user.last_name)
                data = {"status":0,"message":ms}
                return Response(data,status=status.HTTP_200_OK)
            guaranteeserializer = CircleMemberSerializer(guarantee_member,context={'request':request,'circle':circle})
            ms = "{} {} added to guarantee request list".format(guarantee_member.user.first_name,guarantee_member.user.last_name)
            data = {"status":1,'guarantee':guaranteeserializer.data,'message':ms}
            return Response(data,status=status.HTTP_201_CREATED)
        data = {"status":0,"errors":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class AllowedGuaranteeRequestsSetting(APIView):
    """
    Sets allowed public guarantor bool
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        print(request.data)
        serializer = AllowedGuaranteeRequestSerializer(data=request.data)
        if serializer.is_valid():
            allowed = serializer.validated_data['allow_public_guarantees']
            circle = serializer.validated_data['circle_acc_number']
            if allowed == 'true':
                try:
                    CircleMember.objects.filter(circle=circle,member=request.user.member).update(allow_public_guarantees_request=True)
                except Exception as e:
                    data = {"status":0,"message":"Unable to change allowed guarantees setting"}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":1}
                return Response(data,status=status.HTTP_200_OK)
            CircleMember.objects.filter(circle=circle,member=request.user.member).update(allow_public_guarantees_request=False)
            data = {"status":1}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_allowed_guarantee_request(request,*args,**kwargs):
    serializer = AllowedGuaranteeSerializer(data=request.data)
    if serializer.is_valid():
        instance = sms_utils.Sms()
        circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
        phone = instance.format_phone_number(serializer.validated_data['guarantee'])
        user_circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
        guarantee_circle_member = CircleMember.objects.get(circle=circle,member=Member.objects.get(phone_number=phone))
        try:
            AllowedGuarantorRequest.objects.filter(circle_member=user_circle_member,allows_request_from=guarantee_circle_member).delete()
            ms = " {} {} removed from guarantee request list".format(guarantee_circle_member.member.user.first_name,guarantee_circle_member.member.user.last_name)
            data = {"status":1,"message":ms}
            return Response(data,status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            ms = " Unable to remove {} {} from guarantee request list".format(guarantee_circle_member.member.user.first_name,guarantee_circle_member.member.user.last_name)
            data = {"status":0,"message":ms}
            return Response(data,status=status.HTTP_200_OK)
    data = {"status":0,"message":serializer.errors}
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
            acc_number,amount,pin = serializer.validated_data['circle_acc_number'],float(serializer.validated_data['amount']),serializer.validated_data['pin']
            instance = wallet_utils.Wallet()
            valid,response = instance.validate_account(request,pin,amount)
            if valid:
                circle = Circle.objects.get(circle_acc_number=acc_number)
                desc = "Purchased shares worth {} in circle {}".format(amount,circle.circle_name)
                transaction = response
                transaction.transaction_desc = desc
                transaction.recipient = circle.circle_acc_number
                transaction.save()
                try:
                    desc = "Bought shares worth {} from wallet".format(amount)
                    instance = circle_utils.Circle()
                    circle_member = CircleMember.objects.create(circle=circle,member=request.user.member)
                    shares = Shares.objects.create(circle_member=circle_member,num_of_shares=amount)
                    IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="deposit",recipient=circle_member,transaction_time=datetime.datetime.now(),transaction_desc=desc,num_of_shares=amount)
                    instance.check_update_circle_status(circle)
                    CircleInvitation.objects.filter(phone_number=request.user.member.phone_number,invited_by__in=CircleMember.objects.filter(circle=circle).values_list('id',flat=True)).delete()
                    data = {"status":1}
                    return Response(data,status=status.HTTP_200_OK)
                except Exception,e:
                    print(str(e))
                    data = {"status":0,"message":"Unable to add member to circle"}
                    return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status.HTTP_200_OK)


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

class CircleInvite(APIView):
    """
    Sends Invites to contacts provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = CircleInviteSerializer(data=request.data)
        if serializer.is_valid():
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            instance = sms_utils.Sms()
            phone = instance.format_phone_number(serializer.validated_data['phone_number'])
            circle_member = CircleMember.objects.get(member=request.user.member,circle=circle)
            try:
                CircleMember.objects.get(circle=circle,member=Member.objects.get(phone_number=phone))
            except ObjectDoesNotExist:
                CircleInvitation.objects.create(phone_number=phone,invited_by=circle_member)
                ms ="Invitation to {} has been sent".format(phone)
                data = {"status":1,"message":ms}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":"Already exists as a circle member"}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":""}
        return Response(data,status=status.HTTP_200_OK)

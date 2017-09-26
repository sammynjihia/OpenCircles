from django.shortcuts import render
from django.http import Http404
from django.db.models import Q
from django.contrib.auth import login
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from .models import Circle,CircleMember,CircleInvitation,AllowedGuarantorRequest
from member.models import Contacts,Member
from shares.models import Shares,IntraCircleShareTransaction
from wallet.models import Transactions

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication,BasicAuthentication
from rest_framework.authtoken.models import Token

from app_utility import circle_utils,wallet_utils,sms_utils,general_utils,fcm_utils

import datetime,json

# Create your views here.
class CircleCreation(APIView):
    """
    Creates new circle when circle_name,circle_type and contact_list(should be a list/array datatype) are provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        if "contact_list" in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data["contact_list"] = json.loads(request.data["contact_list"])
            contacts = request.data["contact_list"] if "contact_list" in request.data else []
            request.data._mutable = mutable
        serializer = CircleCreationSerializer(data=request.data)
        if serializer.is_valid():
            instance = wallet_utils.Wallet()
            minimum_share = serializer.validated_data['minimum_share']
            if minimum_share < settings.MININIMUM_CIRCLE_SHARES:
                data = {"status":0,"message":"The allowed minimum circle shares is {}".format(settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data,status=status.HTTP_200_OK)
            valid,response = instance.validate_account(request,serializer.validated_data['pin'],minimum_share)
            if valid:
                created_objects=[]
                try:
                    try:
                        last_circle_created = Circle.objects.latest('id')
                        last_acc_number = int(last_circle_created.circle_acc_number)
                        acc_number = last_acc_number + 1
                    except ObjectDoesNotExist:
                        acc_number = 100000
                    member = request.user.member
                    circle = serializer.save(initiated_by=member,circle_acc_number=acc_number)
                    created_objects.append(circle)
                    circle_member = CircleMember.objects.create(member=member,circle=circle)
                    wallet_desc = "Purchased shares worth {} {} in circle {}".format(member.currency,minimum_share,circle.circle_name)
                    shares_desc = "Bought shares worth {} from wallet".format(minimum_share)
                    wallet_transaction = Transactions.objects.create(wallet=member.wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_amount=minimum_share,transaction_desc=wallet_desc,recipient=circle.circle_acc_number)
                    created_objects.append(wallet_transaction)
                    shares = Shares.objects.create(circle_member=circle_member,num_of_shares=minimum_share)
                    shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="DEPOSIT",num_of_shares=minimum_share,transaction_desc=shares_desc,recipient=circle_member)
                    if len(contacts):
                        instance = sms_utils.Sms()
                        circle_invites = [CircleInvitation(invited_by=circle_member,phone_number=phone) for phone in contacts]
                        invites = CircleInvitation.objects.bulk_create(circle_invites)
                    wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                    shares_serializer = SharesTransactionSerializer(shares_transaction)
                    serializer = CircleSerializer(circle,context={'request':request})
                    instance = fcm_utils.Fcm()
                    registration_ids = instance.get_invited_circle_member_token(circle,member)
                    if len(registration_ids):
                        title = circle.circle_name
                        message = "{} {} invited you to join circle {}.".format(member.user.first_name,member.user.last_name,title)
                        device =  "multiple" if len(registration_ids)>1 else "single"
                        inivited_serializer = InvitedCircleSerializer(circle)
                        fcm_data = {"request_type":"INVITED_CIRCLE","circle":serializer.data}
                        instance.notification_push(device,registration_ids,title,message)
                        instance.data_push(device,registration_ids,fcm_data)
                    data={"status":1,"circle":serializer.data,"wallet_transaction":wallet_serializer.data,"shares_transaction":shares_serializer.data}
                    return Response(data,status=status.HTTP_201_CREATED)
                except Exception as e:
                    print(str(e))
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    error = "Unable to create circle"
                    data = {"status":0,"message":error}
                    return Response(data,status = status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data,status = status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status = status.HTTP_200_OK)

class CircleMemberGuaranteeList(APIView):
    """
    Retrieves the circle member guarantee list
    """
    authentication_classes  = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = CircleMemberGuaranteeSerializer(data=request.data)
        if serializer.is_valid():
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            try:
                circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
                guarantees_request = AllowedGuarantorRequest.objects.filter(circle_member=circle_member)
                if guarantees_request.exists():
                    guarantees = [guarantee_request.allows_request_from.member.phone_number for guarantee_request in guarantees_request]
                    data = {"status":1,"guarantees":guarantees}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":1,"guarantees":[]}
                return Response(data,status=status.HTTP_200_OK)
            except CircleMember.DoesNotExist:
                message = "You are not a member of circle %s"%(circle.circle_name)
                data = {"status":0,"message":message}
                return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class CircleMemberDetails(APIView):
    """
    Retrieves circle member details
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes =(IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = CircleMemberDetailsSerializer(data=request.data)
        if serializer.is_valid():
            instance = sms_utils.Sms()
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            member = Member.objects.get(phone_number=instance.format_phone_number(serializer.validated_data['phone_number']))
            try:
                circle_member = CircleMember.objects.get(circle=circle,member=member)
            except CircleMember.DoesNotExist:
                data = {"status":0,"message":"Circle member does not exist"}
                return Response(data,status=status.HTTP_200_OK)
            circle_member_serializer = CircleMemberSerializer(member,context={"request":request,"circle":circle})
            data = {"status":1,"member":circle_member_serializer.data}
            return Response(data,status=status.HTTP_200_OK)

class MemberCircle(APIView):
    """
    Lists member's circles and suggested circles
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        try:
            instance = circle_utils.Circle()
            circles_ids = list(CircleMember.objects.filter(member=request.user.member).values_list('circle',flat=True))
            unjoined_circles = Circle.objects.filter(~Q(id__in=circles_ids))
            contacts = Contacts.objects.filter(member=request.user.member,is_member=True).values_list('phone_number',flat=True)
            suggested_circles = instance.get_suggested_circles(unjoined_circles,contacts)
            suggested_ids = [key.id for key,value in suggested_circles]
            invited_circles = instance.get_invited_circles(request,unjoined_circles)
            invited_circles_ids  = [circle.id for circle in invited_circles]
            unjoined_ids = list(set(invited_circles_ids+suggested_ids))
            suggested_circles_ids = unjoined_ids + circles_ids
            circles = Circle.objects.filter(id__in=suggested_circles_ids)
            circle_serializer = CircleSerializer(circles,many=True,context={"request":request})
        except Exception as e:
            print(str(e))
            data = {"status":0,"message":"Unable to fetch circle list"}
            return Response(data,status = status.HTTP_200_OK)
        data={"status":1,"circles":circle_serializer.data}
        return Response(data,status = status.HTTP_200_OK)

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
                        circle.is_active=True
                        circle.save()
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
        serializer = AllowedGuaranteeSerializer(data=request.data)
        if serializer.is_valid():
            instance = sms_utils.Sms()
            circle,guarantee_phone,member = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number']),instance.format_phone_number(serializer.validated_data['guarantee']),request.user.member
            if guarantee_phone == member.phone_number:
                data = {"status":0,"message":"Unable to add yourself to guarantee request list"}
                return Response(data,status=status.HTTP_200_OK)
            user_circle_member = CircleMember.objects.get(circle=circle,member=member)
            guarantee_member = Member.objects.get(phone_number=guarantee_phone)
            allowed_guarantee = CircleMember.objects.get(circle=circle,member=guarantee_member)
            try:
                AllowedGuarantorRequest.objects.create(circle_member=user_circle_member,allows_request_from=allowed_guarantee)
                guarantee_serializer = CircleMemberSerializer(guarantee_member,context={"request":request,"circle":circle})
                ms = "{} {} added to guarantee request list".format(guarantee_member.user.first_name,guarantee_member.user.last_name)
                data = {"status":1,'guarantee':guarantee_serializer.data,'message':ms}
                instance = fcm_utils.Fcm()
                registration_id = guarantee_member.device_token
                fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"allow_guarantor_request":True}
                instance.data_push("single",registration_id,fcm_data)
            except Exception as e:
                print (str(e))
                ms = "Unable to add {} {} to guarantee request list".format(guarantee_member.user.first_name,guarantee_member.user.last_name)
                data = {"status":0,"message":ms}
                return Response(data,status=status.HTTP_200_OK)
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
        serializer = AllowedGuaranteeRequestSerializer(data=request.data)
        if serializer.is_valid():
            allowed = serializer.validated_data['allow_public_guarantees']
            circle,member = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number']),request.user.member
            if allowed == 'true':
                try:
                    CircleMember.objects.filter(circle=circle,member=member).update(allow_public_guarantees_request=True)
                    instance = fcm_utils.Fcm()
                    circle_members = CircleMember.objects.filter(circle=circle)
                    registration_ids = instance.get_circle_members_token(circle,member)
                    fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"allow_guarantor_request":True}
                    instance.data_push("multiple",registration_ids,fcm_data)
                except Exception as e:
                    print(str(e))
                    data = {"status":0,"message":"Unable to change allowed guarantees setting"}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":1}
                return Response(data,status=status.HTTP_200_OK)
            instance = fcm_utils.Fcm()
            circle_members = CircleMember.objects.filter(circle=circle)
            registration_ids = instance.get_circle_members_token(circle,member)
            fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"allow_guarantor_request":False}
            instance.data_push("multiple",registration_ids,fcm_data)
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
        phone_number = instance.format_phone_number(serializer.validated_data['guarantee'])
        user_circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
        guarantee_circle_member = CircleMember.objects.get(circle=circle,member=Member.objects.get(phone_number=phone_number))
        try:
            AllowedGuarantorRequest.objects.filter(circle_member=user_circle_member,allows_request_from=guarantee_circle_member).delete()
            message = " {} {} removed from guarantee request list".format(guarantee_circle_member.member.user.first_name,guarantee_circle_member.member.user.last_name)
            data = {"status":1,"message":message}
            instance = fcm_utils.Fcm()
            registration_id = guarantee_circle_member.member.device_token
            fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST","circle_acc_number":circle.circle_acc_number,"phone_number":phone_number,"allow_guarantor_request":False}
            instance.data_push("single",registration_id,fcm_data)
            return Response(data,status=status.HTTP_200_OK)
        except Exception as e:
            print(str(e))
            message = " Unable to remove {} {} from guarantee request list".format(guarantee_circle_member.member.user.first_name,guarantee_circle_member.member.user.last_name)
            data = {"status":0,"message":message}
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
            acc_number,amount,pin = serializer.validated_data['circle_acc_number'],serializer.validated_data['amount'],serializer.validated_data['pin']
            circle = Circle.objects.get(circle_acc_number=acc_number)
            if amount < circle.minimum_share:
                data = {"status":0,"message":"The allowed minimum shares for {} circle is {}".format(circle.circle_name,settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data,status=status.HTTP_200_OK)
            instance = wallet_utils.Wallet()
            valid,response = instance.validate_account(request,pin,amount)
            if valid:
                created_objects = []
                try:
                    member=request.user.member
                    wallet_desc = "Purchased shares worth {} {} in circle {}".format(member.currency,amount,circle.circle_name)
                    shares_desc = "Bought shares worth {} from wallet".format(amount)
                    instance = circle_utils.Circle()
                    circle_member = CircleMember.objects.create(circle=circle,member=member)
                    created_objects.append(circle_member)
                    wallet_transaction = Transactions.objects.create(wallet=request.user.member.wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_amount=amount,transaction_desc=wallet_desc,recipient=circle.circle_acc_number)
                    created_objects.append(wallet_transaction)
                    shares = Shares.objects.create(circle_member=circle_member,num_of_shares=amount)
                    shares_transaction =IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="DEPOSIT",recipient=circle_member,transaction_time=datetime.datetime.now(),transaction_desc=shares_desc,num_of_shares=amount)
                    instance.check_update_circle_status(circle)
                    CircleInvitation.objects.filter(phone_number=request.user.member.phone_number,invited_by__in=CircleMember.objects.filter(circle=circle).values_list('id',flat=True)).delete()
                    wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                    shares_serializer = SharesTransactionSerializer(shares_transaction)
                    instance = fcm_utils.Fcm()
                    registration_ids = instance.get_circle_members_token(circle,member)
                    circle_member_serializer = UnloggedCircleMemberSerializer(member,context={"circle":circle})
                    fcm_data = {"request_type":"NEW_CIRCLE_MEMBERSHIP","circle_acc_number":circle.circle_acc_number,"circle_member":circle_member_serializer.data}
                    instance.data_push("mutiple",registration_ids,fcm_data)
                    data = {"status":1,"wallet_transaction":wallet_serializer.data,"shares_transaction":shares_serializer.data}
                    return Response(data,status=status.HTTP_200_OK)
                except Exception,e:
                    print(str(e))
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    data = {"status":0,"message":"Unable to add member to circle"}
                    return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status.HTTP_200_OK)


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
        data = {"status":0,"message":serializer.erors}
        return Response(data,status=status.HTTP_200_OK)

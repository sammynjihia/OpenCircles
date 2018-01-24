from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings

from circle.models import Circle,CircleMember,CircleInvitation,AllowedGuarantorRequest,DeclinedCircles
from member.models import Contacts,Member
from shares.models import Shares,IntraCircleShareTransaction
from wallet.models import Transactions, ReferralFee

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication,BasicAuthentication


from app_utility import circle_utils, wallet_utils, sms_utils, general_utils, fcm_utils, member_utils, loan_utils

import datetime,json

from circle.tasks import send_circle_invites, referral_programme_promotion

from loan.tasks import updating_loan_limit

# Create your views here.
class CircleCreation(APIView):
    """
    Creates new circle when circle_name,circle_type and contact_list(should be a list/array datatype) are provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        if "contact_list" in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data["contact_list"] = json.loads(request.data["contact_list"])
            request.data["loan_tariff"] = json.loads(request.data["loan_tariff"])
            circle_loan_tariff = request.data["loan_tariff"]
            contacts = request.data["contact_list"] if "contact_list" in request.data else []
            request.data._mutable = mutable
        serializer = CircleCreationSerializer(data=request.data)
        if serializer.is_valid():
            wallet_instance = wallet_utils.Wallet()
            minimum_share = serializer.validated_data['minimum_share']
            if minimum_share < settings.MININIMUM_CIRCLE_SHARES:
                data = {"status":0, "message":"The allowed minimum circle deposit is {} {}".format(
                                                                                                request.user.member.currency,
                                                                                                settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data, status=status.HTTP_200_OK)
            valid, response = wallet_instance.validate_account(request, serializer.validated_data['pin'], minimum_share)
            if valid:
                created_objects=[]
                try:
                    try:
                        last_circle_created = Circle.objects.latest('id')
                        last_acc_number = int(last_circle_created.circle_acc_number)
                        acc_number = last_acc_number + 1
                    except ObjectDoesNotExist:
                        acc_number = 100000
                    general_instance = general_utils.General()
                    member = request.user.member
                    circle = serializer.save(initiated_by=member, circle_acc_number=acc_number)
                    created_objects.append(circle)
                    circle_member = CircleMember.objects.create(member=member, circle=circle)
                    wallet_transaction_code = general_instance.generate_unique_identifier('WTD')
                    wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) - minimum_share
                    wallet_desc = "{} confirmed.You have purchased shares worth {} {} in circle {}." \
                                  "New wallet balance is {} {}.".format(
                                                                    wallet_transaction_code,
                                                                    member.currency,
                                                                    minimum_share,
                                                                    circle.circle_name,
                                                                    member.currency,
                                                                    wallet_balance)
                    shares_transaction_code = general_instance.generate_unique_identifier('STD')
                    shares_desc = "{} confirmed.You have purchased shares worth {} {}.".format(
                                                                                            shares_transaction_code,
                                                                                            member.currency,
                                                                                            minimum_share)
                    wallet_transaction = Transactions.objects.create(
                                            wallet=member.wallet,
                                            transaction_type="DEBIT",
                                            transaction_time=datetime.datetime.now(),
                                            transaction_amount=minimum_share,
                                            transaction_desc=wallet_desc,
                                            recipient=circle.circle_acc_number,
                                            transaction_code=wallet_transaction_code,
                                            source="wallet")
                    created_objects.append(wallet_transaction)
                    shares = Shares.objects.create(circle_member=circle_member)
                    shares_transaction = IntraCircleShareTransaction.objects.create(
                                                                                shares=shares,
                                                                                transaction_type="DEPOSIT",
                                                                                num_of_shares=minimum_share,
                                                                                transaction_desc=shares_desc,
                                                                                recipient=circle_member,
                                                                                transaction_code=shares_transaction_code)

                    if len(contacts):
                        member_instance = member_utils.OpenCircleMember()
                        circle_invites = [CircleInvitation(
                                            invited_by=circle_member,
                                            phone_number=phone,
                                            is_member=member_instance.get_is_member(phone)) for phone in contacts]
                        invites = CircleInvitation.objects.bulk_create(circle_invites)
                        id_list = [invite.id for invite in invites]
                        send_circle_invites.delay(id_list)
                    wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                    shares_serializer = SharesTransactionSerializer(shares_transaction)
                    circle_serializer = CircleSerializer(circle, context={'request':request})
                    circle_instance = circle_utils.Circle()
                    circle_instance.save_loan_tariff(circle, circle_loan_tariff)
                    circle = circle_serializer.data
                    wallet_transaction = wallet_serializer.data
                    shares_transaction = shares_serializer.data
                    data={
                        "status":1,
                        "circle":circle,
                        "wallet_transaction":wallet_transaction,
                        "shares_transaction":shares_transaction,
                        "message":"Circle created successfully.Circle will be activated when atleast four members join."
                    }
                    return Response(data,status=status.HTTP_201_CREATED)
                except Exception as e:
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    error = "Unable to create circle"
                    data = {"status":0, "message":error}
                    return Response(data, status = status.HTTP_200_OK)
            data = {"status":0, "message":response}
            return Response(data, status = status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status = status.HTTP_200_OK)

class CircleMemberGuaranteeList(APIView):
    """
    Retrieves the circle member guarantee list
    """
    authentication_classes  = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = CircleMemberGuaranteeSerializer(data=request.data)
        if serializer.is_valid():
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            try:
                circle_member = CircleMember.objects.get(circle=circle, member=request.user.member)
                guarantees_request = AllowedGuarantorRequest.objects.filter(circle_member=circle_member)
                if guarantees_request.exists():
                    guarantees = [guarantee_request.allows_request_from.member.phone_number for guarantee_request in guarantees_request]
                    data = {"status":1, "guarantees":guarantees}
                    return Response(data, status=status.HTTP_200_OK)
                data = {"status":1, "guarantees":[]}
                return Response(data, status=status.HTTP_200_OK)
            except CircleMember.DoesNotExist:
                message = "You are not a member of circle %s"%(circle.circle_name)
                data = {"status":0, "message":message}
                return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class CircleMemberDetails(APIView):
    """
    Retrieves circle member details
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = CircleMemberDetailsSerializer(data=request.data)
        if serializer.is_valid():
            instance = sms_utils.Sms()
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            member = Member.objects.get(phone_number=instance.format_phone_number(
                                                                serializer.validated_data['phone_number']))
            try:
                CircleMember.objects.get(circle=circle, member=member)
            except CircleMember.DoesNotExist:
                data = {"status":0, "message":"Circle member does not exist"}
                return Response(data, status=status.HTTP_200_OK)
            circle_member_serializer = CircleMemberSerializer(member, context={"request":request, "circle":circle})
            data = {"status":1, "member":circle_member_serializer.data}
            return Response(data, status=status.HTTP_200_OK)

class MemberCircle(APIView):
    """
    Lists member's circles and suggested circles
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        try:
            instance = circle_utils.Circle()
            circles_ids = list(CircleMember.objects.filter(member=request.user.member).values_list('circle',flat=True))
            declined_ids = list(DeclinedCircles.objects.filter(member=request.user.member).values_list('circle',flat=True))
            total_ids = circles_ids + declined_ids
            unjoined_circles = Circle.objects.filter(~Q(id__in=total_ids))
            invited_circles = instance.get_invited_circles(request)
            invited_circles_ids  = [circle.id for circle in invited_circles]
            total_suggested_circle_count = len(circles_ids) + len(invited_circles_ids)
            suggested_ids = []
            if total_suggested_circle_count < settings.MAXIMUM_SUGGESTED_CIRCLE:
                diff = settings.MAXIMUM_SUGGESTED_CIRCLE - total_suggested_circle_count
                contacts = Contacts.objects.filter(
                                                member=request.user.member,
                                                is_member=True).values_list('phone_number',flat=True)
                suggested_circles = instance.get_suggested_circles(unjoined_circles, contacts, request, diff)
                if len(suggested_circles):
                    suggested_ids = [key.id for key, value in suggested_circles]
            suggested_circles_ids = invited_circles_ids + suggested_ids + circles_ids
            circles = Circle.objects.filter(id__in=suggested_circles_ids)
            circle_serializer = CircleSerializer(circles, many=True, context={"request":request})
        except Exception as e:
            print(str(e))
            data = {"status":0, "message":"Unable to fetch circle list"}
            return Response(data, status = status.HTTP_200_OK)
        data={"status":1, "circles":circle_serializer.data}
        return Response(data, status = status.HTTP_200_OK)

class CircleInvitationResponse(APIView):
    """
    Declines circle invitation
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request):
        serializer = CircleInvitationSerializer(data=request.data)
        if serializer.is_valid():
            circle = Circle.objects.get(circle_acc_number = serializer.validated_data['circle_acc_number'])
            circle_invites = CircleInvitation.objects.filter(
                                                        invited_by__in = CircleMember.objects.filter(circle=circle),
                                                        phone_number=request.user.member.phone_number)
            if circle_invites.exists():
                circle_invites.update(status="Declined")
            else:
                DeclinedCircles.objects.create(circle=circle, member=request.user.member)
            data = {"status":1}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class AllowedGuaranteeRegistration(APIView):
    """
    Adds guarantees
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        serializer = AllowedGuaranteeSerializer(data=request.data)
        if serializer.is_valid():
            instance = sms_utils.Sms()
            circle, guarantee_phone, member = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number']), instance.format_phone_number(serializer.validated_data['guarantee']), request.user.member
            if guarantee_phone == member.phone_number:
                data = {"status":0,"message":"Unable to add yourself to guarantee request list"}
                return Response(data,status=status.HTTP_200_OK)
            user_circle_member = CircleMember.objects.get(circle=circle, member=member)
            guarantee_member = Member.objects.get(phone_number=guarantee_phone)
            allowed_guarantee = CircleMember.objects.get(circle=circle, member=guarantee_member)
            try:
                AllowedGuarantorRequest.objects.create(
                                                    circle_member=user_circle_member,
                                                    allows_request_from=allowed_guarantee)
                guarantee_serializer = CircleMemberSerializer(
                                            guarantee_member,
                                            context={"request":request,"circle":circle})
                ms = "{} {} added to guarantee request list".format(
                                                                guarantee_member.user.first_name,
                                                                guarantee_member.user.last_name)
                data = {"status":1, 'guarantee':guarantee_serializer.data, 'message':ms}
            except Exception as e:
                print (str(e))
                ms = "Unable to add {} {} to guarantee request list".format(
                                                                        guarantee_member.user.first_name,
                                                                        guarantee_member.user.last_name)
                data = {"status":0, "message":ms}
                return Response(data, status=status.HTTP_200_OK)
            fcm_instance = fcm_utils.Fcm()
            registration_id = guarantee_member.device_token
            fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST",
                        "circle_acc_number":circle.circle_acc_number,
                        "phone_number":member.phone_number,
                        "allow_guarantor_request":True}
            fcm_instance.data_push("single", registration_id, fcm_data)
            print(fcm_data)
            updating_loan_limit.delay(circle.id, member.id)
            return Response(data, status=status.HTTP_201_CREATED)
        data = {"status":0, "errors":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class AllowedGuaranteeRequestsSetting(APIView):
    """
    Sets allowed public guarantor bool
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = AllowedGuaranteeRequestSerializer(data=request.data)
        if serializer.is_valid():
            allowed = serializer.validated_data['allow_public_guarantees']
            circle, member = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number']), request.user.member
            if allowed == 'true':
                try:
                    circle_member = CircleMember.objects.get(circle=circle, member=member)
                    CircleMember.objects.filter(
                                            circle=circle,
                                            member=member).update(allow_public_guarantees_request=True)
                    AllowedGuarantorRequest.objects.filter(circle_member=circle_member).delete()
                except Exception as e:
                    print(str(e))
                    CircleMember.objects.filter(
                                            circle=circle,
                                            member=member).update(allow_public_guarantees_request=False)
                    data = {"status":0, "message":"Unable to change allowed guarantees setting"}
                    return Response(data, status=status.HTTP_200_OK)
                fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST",
                            "circle_acc_number":circle.circle_acc_number,
                            "phone_number":member.phone_number,
                            "allow_guarantor_request":True}
                fcm_instance = fcm_utils.Fcm()
                registration_ids = fcm_instance.get_circle_members_token(circle, member)
                fcm_instance.data_push("multiple", registration_ids, fcm_data)
                print(fcm_data)
                updating_loan_limit.delay(circle.id, member.id)
                data = {"status":1}
                return Response(data, status=status.HTTP_200_OK)
            fcm_instance = fcm_utils.Fcm()
            registration_ids = fcm_instance.get_circle_members_token(circle, member)
            fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST",
                        "circle_acc_number":circle.circle_acc_number,
                        "phone_number":member.phone_number,
                        "allow_guarantor_request":False}
            fcm_instance.data_push("multiple", registration_ids, fcm_data)
            print(fcm_data)
            updating_loan_limit.delay(circle.id, member.id)
            CircleMember.objects.filter(circle=circle, member=member).update(allow_public_guarantees_request=False)
            data = {"status":1}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_allowed_guarantee_request(request):
    serializer = AllowedGuaranteeSerializer(data=request.data)
    if serializer.is_valid():
        member = request.user.member
        instance = sms_utils.Sms()
        circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
        phone_number = instance.format_phone_number(serializer.validated_data['guarantee'])
        user_circle_member = CircleMember.objects.get(circle=circle, member=member)
        guarantee_circle_member = CircleMember.objects.get(circle=circle,
                                                           member=Member.objects.get(phone_number=phone_number))
        try:
            AllowedGuarantorRequest.objects.filter(circle_member=user_circle_member,
                                                   allows_request_from=guarantee_circle_member).delete()
            message = " {} {} removed from guarantee request list".format(
                                                                        guarantee_circle_member.member.user.first_name,
                                                                        guarantee_circle_member.member.user.last_name)
            data = {"status":1, "message":message}
        except Exception as e:
            print(str(e))
            message = " Unable to remove {} {} from guarantee request list".format(
                                                                                guarantee_circle_member.member.user.first_name,
                                                                                guarantee_circle_member.member.user.last_name)
            data = {"status":0, "message":message}
            return Response(data, status=status.HTTP_200_OK)
        fcm_instance = fcm_utils.Fcm()
        registration_id = guarantee_circle_member.member.device_token
        fcm_data = {"request_type":"UPDATE_ALLOW_GUARANTOR_REQUEST",
                    "circle_acc_number":circle.circle_acc_number,
                    "phone_number":member.phone_number,
                    "allow_guarantor_request":False}
        fcm_instance.data_push("single", registration_id, fcm_data)
        print(fcm_data)
        updating_loan_limit.delay(circle.id, member.id)
        return Response(data, status=status.HTTP_200_OK)
    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)

class JoinCircle(APIView):
    """
    Adds member to circle
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request):
        serializer = JoinCircleSerializer(data=request.data)
        if serializer.is_valid():
            acc_number, amount, pin = serializer.validated_data['circle_acc_number'], serializer.validated_data['amount'], serializer.validated_data['pin']
            circle = Circle.objects.get(circle_acc_number=acc_number)
            circle_members_count = CircleMember.objects.filter(circle=circle).count()
            if circle_members_count <= settings.MAX_CIRCLE_MEMBER:
                if amount < circle.minimum_share:
                    data = {"status":0, "message":"The allowed minimum initial deposit for circle " \
                                                  "{} is KES {}".format(circle.circle_name, circle.minimum_share)}
                    return Response(data,status=status.HTTP_200_OK)
                wallet_instance = wallet_utils.Wallet()
                valid,response = wallet_instance.validate_account(request,pin,amount)
                if valid:
                    created_objects = []
                    try:
                        loan_instance = loan_utils.Loan()
                        general_instance = general_utils.General()
                        member = request.user.member
                        existing_circle_member = CircleMember.objects.filter(member=member)
                        wallet_transaction_code = general_instance.generate_unique_identifier('WTD')
                        shares_transaction_code = general_instance.generate_unique_identifier('STD')
                        wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) - amount
                        wallet_desc = "{} confirmed. You have purchased shares worth {} {} in circle {}. " \
                                      "New wallet balance is {} {}.".format(wallet_transaction_code,
                                                                            member.currency, amount,
                                                                            circle.circle_name,
                                                                            member.currency, wallet_balance)
                        shares_desc = "{} confirmed. You have purchased shares " \
                                      "worth {} {}".format(shares_transaction_code, member.currency, amount)
                        circle_instance = circle_utils.Circle()
                        circle_member = CircleMember.objects.create(circle=circle, member=member)
                        created_objects.append(circle_member)
                        wallet_transaction = Transactions.objects.create(wallet=request.user.member.wallet,
                                                                         transaction_type="DEBIT",
                                                                         transaction_time=datetime.datetime.now(),
                                                                         transaction_amount=amount,
                                                                         transaction_desc=wallet_desc,
                                                                         recipient=circle.circle_acc_number,
                                                                         transaction_code=wallet_transaction_code,
                                                                         source="wallet")
                        created_objects.append(wallet_transaction)
                        shares = Shares.objects.create(circle_member=circle_member)
                        shares_transaction =IntraCircleShareTransaction.objects.create(
                                                                                    shares=shares,
                                                                                    transaction_type="DEPOSIT",
                                                                                    recipient=circle_member,
                                                                                    transaction_time=datetime.datetime.now(),
                                                                                    transaction_desc=shares_desc,
                                                                                    num_of_shares=amount,
                                                                                    transaction_code=shares_transaction_code)
                        wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                        shares_serializer = SharesTransactionSerializer(shares_transaction)
                        circle_member_serializer = UnloggedCircleMemberSerializer(member, context={"circle":circle})
                        loan_limit = loan_instance.calculate_loan_limit(circle, member)
                        fcm_instance = fcm_utils.Fcm()
                        old_circle_status = circle.is_active
                        is_active = old_circle_status
                        if not old_circle_status:
                            new_circle_status = circle_instance.check_update_circle_status(circle)
                            if new_circle_status:
                                fcm_data = {"request_type":"UPDATE_CIRCLE_STATUS",
                                            "circle_acc_number":circle.circle_acc_number,
                                            "is_active":True}
                                is_active = True
                                registration_ids = fcm_instance.get_circle_members_token(circle, None)
                                fcm_instance.data_push("mutiple", registration_ids, fcm_data)
                                print(fcm_data)
                        # unblock task
                        updating_loan_limit.delay(circle.id,member.id)
                        fcm_data = {"request_type":"NEW_CIRCLE_MEMBERSHIP",
                                    "circle_acc_number":circle.circle_acc_number,
                                    "circle_member":circle_member_serializer.data}
                        registration_ids = fcm_instance.get_circle_members_token(circle, member)
                        fcm_instance.data_push("mutiple", registration_ids, fcm_data)
                        print(fcm_data)
                        if existing_circle_member.exists():
                            try:
                                is_invited = CircleInvitation.objects.get(phone_number=member.phone_number,
                                                                          invited_by__circle=circle)
                                referral_fee = settings.REFERRAL_FEE
                                today = datetime.date.today()
                                if is_invited.time_invited.date() == today and today.weekday() == 4:
                                    referral_fee = settings.FRIDAY_REFERRAL_FEE
                                referral_programme_promotion.delay(is_invited.id, referral_fee)
                            except CircleInvitation.DoesNotExist:
                                print("object does not exist")
                            except CircleInvitation.MultipleObjectsReturned:
                                ReferralFee.objects.create( member=member,
                                                            circle=circle,
                                                            is_disbursed=False,
                                                            extra_info="user has been invited by more than one circle member")
                        data = {"status":1,
                                "wallet_transaction":wallet_serializer.data,
                                "shares_transaction":shares_serializer.data,
                                "loan_limit":loan_limit,
                                "is_active":is_active}
                    except Exception as e:
                        print(str(e))
                        instance = general_utils.General()
                        instance.delete_created_objects(created_objects)
                        data = {"status":0, "message":"Unable to add member to circle"}
                        return Response(data, status=status.HTTP_200_OK)
                    fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                    fcm_instance = fcm_utils.Fcm()
                    fcm_data = {"request_type": "UPDATE_AVAILABLE_SHARES",
                                "circle_acc_number": circle.circle_acc_number,
                                "phone_number": member.phone_number,
                                "available_shares": fcm_available_shares}
                    registration_ids = fcm_instance.get_circle_members_token(circle, member)
                    fcm_instance.data_push("multiple", registration_ids, fcm_data)
                    return Response(data, status=status.HTTP_200_OK)
                data = {"status":0, "message":response}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":"Unable to join circle.The circle is already full."}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status.HTTP_200_OK)


class CircleInvite(APIView):
    """
    Sends Invites to contacts provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = CircleInviteSerializer(data=request.data)
        if serializer.is_valid():
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            sms_instance = sms_utils.Sms()
            phone = sms_instance.format_phone_number(serializer.validated_data['phone_number'])
            circle_member = CircleMember.objects.get(member=request.user.member, circle=circle)
            try:
                CircleMember.objects.get(circle=circle, member=Member.objects.filter(phone_number=phone))
                data = {"status":0, "message":"The user is already a member of the circle."}
            except CircleMember.DoesNotExist:
                invites = CircleInvitation.objects.filter(invited_by__in = CircleMember.objects.filter(circle=circle),
                                                          phone_number=phone)
                if invites.exists():
                    invite = invites.latest('id')
                    if invite.status == "Pending":
                        data = {"status":0, "message":"Unable to send invitation."
                                                     "Member has already been invited to join this circle."}
                    else:
                        data = {"status":0, "message":"Unable to send invitation."
                                                     "Member already declined previous circle invitation"}
                else:
                    created_objects = []
                    try:
                        member_instance = member_utils.OpenCircleMember()
                        circle_invite = CircleInvitation.objects.create(phone_number=phone,
                                                                        invited_by=circle_member,
                                                                        is_member=member_instance.get_is_member(phone))
                        print(circle_invite)
                        created_objects.append(circle_invite)
                        try:
                            invited_member = Member.objects.get(phone_number=phone)
                            DeclinedCircles.objects.filter(circle=circle, member=invited_member).delete()
                            registration_id = invited_member.device_token
                            if len(registration_id):
                                fcm_instance = fcm_utils.Fcm()
                                invited_by = "{} {}".format(request.user.first_name, request.user.last_name)
                                invited_serializer = InvitedCircleSerializer(circle, context={"invited_by":invited_by})
                                fcm_data = {"request_type":"NEW_CIRCLE_INVITATION",
                                            "circle":invited_serializer.data}
                                fcm_instance.data_push("single", registration_id, fcm_data)
                            else:
                                message = "{} {} has invited you to join circle {} on " \
                                          "Opencircles.".format(request.user.first_name,
                                                                request.user.last_name,
                                                                circle.circle_name)
                                sms_instance.sendsms(phone, message)
                        except Member.DoesNotExist:
                            #send sms
                            message = "{} {} has invited you to join circle {} on Opencircles." \
                                      "Opencircles is a peer to peer credit and savings platform that makes you " \
                                      "and your close friends, family and colleagues into investment and " \
                                      "saving partners.Get it on {} ".format(request.user.first_name,
                                                                             request.user.last_name,
                                                                             circle.circle_name,
                                                                             settings.APP_STORE_LINK)
                            sms_instance.sendsms(phone, message)
                        ms ="Invitation to {} has been sent.".format(phone)
                        data = {"status":1, "message":ms}
                    except Exception as e:
                        print(str(e))
                        general_utils.General().delete_created_objects(created_objects)
                        data = {"status":0, "message":"Unable to send circle invitation"}
                return Response(data, status=status.HTTP_200_OK)
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.erors}
        return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def check_circle_name(request):
    request.data._mutable = True
    request.data["circle_name"] = request.data["circle_name"].lower()
    serializer = CircleNameSerializer(data=request.data)
    if serializer.is_valid():
        data = {"status":1}
        return Response(data, status=status.HTTP_200_OK)
    message = "".join(serializer.errors["circle_name"])
    data = {"status":0, "message":message}
    return Response(data, status=status.HTTP_200_OK)

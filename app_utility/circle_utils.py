from django.db.models import Sum
from django.conf import settings

from member.models import Member
from circle.models import Circle as CircleModel,CircleMember,CircleInvitation,DeclinedCircles
from shares.models import Shares,IntraCircleShareTransaction
from loan.models import LoanTariff,GuarantorRequest,LoanApplication
from app_utility import fcm_utils,sms_utils
from django.db.models import Q
#from circle import serializers
from circle.serializers import *
from dateutil.relativedelta import relativedelta


import operator, re, datetime

class Circle():
    def get_suggested_circles(self,unjoined_circles,contacts,request,suggested_num):
        suggested_circles={}
        unjoined_circles = unjoined_circles.filter(circle_type="OPEN")
        circle_invites_ids = CircleInvitation.objects.filter(phone_number=request.user.member.phone_number).values_list("invited_by__circle",flat=True)
        invited_circles = CircleModel.objects.filter(id__in = circle_invites_ids)
        unjoined_circles = [ circle for circle in unjoined_circles if circle not in invited_circles]
        suggested_circles = {}
        if len(unjoined_circles):
            suggested_num = suggested_num if(len(unjoined_circles)) > suggested_num else len(unjoined_circles)
            for circle in unjoined_circles:
                circle_count = CircleMember.objects.filter(circle=circle,member_id__in=Member.objects.filter(phone_number__in=contacts).values_list('id',flat=True)).count()
                suggested_circles[circle]=circle_count
            suggested_circles = sorted(suggested_circles.items(),key=operator.itemgetter(1),reverse=True)[0:suggested_num]
        return suggested_circles

    def check_update_circle_status(self,circle):
        if not circle.is_active:
            if CircleMember.objects.filter(circle=circle).count() >= settings.MIN_NUM_CIRCLE_MEMBER:
                circle.is_active=True
                circle.save()
                return True
            return False
        return True

    def get_invited_circles(self,request,unjoined_circles):
        circles_ids = CircleInvitation.objects.filter(phone_number=request.user.member.phone_number,status="Pending").values_list("invited_by__circle",flat=True)
        invited_circles = CircleModel.objects.filter(id__in = circles_ids)
        return invited_circles


    def get_available_circle_shares(self,circle):
        shares = Shares.objects.filter(circle_member__circle=circle)
        transactions = IntraCircleShareTransaction.objects.filter(shares__in=shares)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        locked = transactions.filter(transaction_type="LOCKED").aggregate(total=Sum('num_of_shares'))
        total_locked = 0 if locked['total'] is None else locked['total']
        unlocked = transactions.filter(transaction_type="UNLOCKED").aggregate(total=Sum('num_of_shares'))
        total_unlocked = 0 if unlocked['total'] is None else unlocked['total']
        available_shares = (total_deposits-total_transfers-total_withdraws)-(total_locked-total_unlocked)
        return available_shares

    def get_total_circle_member_shares(self,circle,member,date):
        try:
            circle_member = CircleMember.objects.get(circle=circle,member=member)
        except CircleMember.DoesNotExist:
            return 0
        shares = circle_member.shares.get()
        if date is None:
            transactions = IntraCircleShareTransaction.objects.filter(shares=shares)
        else:
            transactions = IntraCircleShareTransaction.objects.filter(shares=shares,transaction_time__lt=date)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        total_shares = (total_deposits-total_transfers-total_withdraws)
        return total_shares

    def get_total_circle_shares(self,circle,date,member):
        if date is None:
            transactions = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle)
        else:
            transactions = IntraCircleShareTransaction.objects.filter(~Q(shares__circle_member__member=member)).filter(shares__circle_member__circle=circle,transaction_time__lt=date)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        total_shares = (total_deposits-total_transfers-total_withdraws)
        return total_shares


    def get_available_circle_member_shares(self,circle,member):
        try:
            circle_member = CircleMember.objects.get(circle=circle,member=member)
        except CircleMember.DoesNotExist:
            return 0
        shares = circle_member.shares.get()
        transactions = IntraCircleShareTransaction.objects.filter(shares=shares)
        deposits = transactions.filter(transaction_type="DEPOSIT").aggregate(total=Sum('num_of_shares'))
        total_deposits = 0 if deposits['total'] is None else deposits['total']
        transfers = transactions.filter(transaction_type="TRANSFER").aggregate(total=Sum('num_of_shares'))
        total_transfers = 0 if transfers['total'] is None else transfers['total']
        withdraws = transactions.filter(transaction_type="WITHDRAW").aggregate(total=Sum('num_of_shares'))
        total_withdraws = 0 if withdraws['total'] is None else withdraws['total']
        locked = transactions.filter(transaction_type="LOCKED").aggregate(total=Sum('num_of_shares'))
        total_locked = 0 if locked['total'] is None else locked['total']
        unlocked = transactions.filter(transaction_type="UNLOCKED").aggregate(total=Sum('num_of_shares'))
        total_unlocked = 0 if unlocked['total'] is None else unlocked['total']
        available_shares = (total_deposits-total_transfers-total_withdraws)-(total_locked-total_unlocked)
        return available_shares

    def get_guarantor_available_shares(self,circle,member):
        actual_available_shares = self.get_available_circle_member_shares(circle,member)
        circle_member = CircleMember.objects.get(circle=circle,member=member)
        requests = GuarantorRequest.objects.filter(circle_member=circle_member,has_accepted=None)
        if requests.exists():
            amount = requests.aggregate(total=Sum('num_of_shares'))
            return actual_available_shares - amount['total']
        return actual_available_shares

    def save_loan_tariff(self,circle,loan_data):
        loan_tariffs = [LoanTariff(max_amount=int(self.extract_amount(data["range"])[1]),min_amount=int(self.extract_amount(data["range"])[0]),num_of_months=data['months'],monthly_interest_rate=data['interest'],circle=circle) for data in loan_data]
        loan_tariffs = LoanTariff.objects.bulk_create(loan_tariffs)
        return loan_tariffs

    def extract_amount(self,loan_range):
        new_range = re.findall(r'\d+',loan_range)
        return new_range

    def send_circle_invitation(self, circle_invitations):
        for invite in circle_invitations:
            circle, member = invite.invited_by.circle, invite.invited_by.member
            if invite.is_member:
                invited_member = Member.objects.get(phone_number=invite.phone_number)
                DeclinedCircles.objects.filter(circle=circle,member=invited_member).delete()
                registration_id = invited_member.device_token
                if len(registration_id):
                    fcm_instance = fcm_utils.Fcm()
                    invited_by = "{} {}".format(member.user.first_name,member.user.last_name)
                    invited_serializer = serializers.InvitedCircleSerializer(circle,context={"invited_by":invited_by})
                    fcm_data = {"request_type":"NEW_CIRCLE_INVITATION","circle":invited_serializer.data}
                    print(fcm_data)
                    fcm_instance.data_push("single",registration_id,fcm_data)
                else:
                    sms_instance = sms_utils.Sms()
                    message = "{} {} has invited you to join circle {} on Opencircles.".format(member.user.first_name, member.user.last_name, circle.circle_name)
                    sms_instance.sendsms(invite.phone_number,message)
            else:
                #send sms
                sms_instance = sms_utils.Sms()
                message =  "{} {} has invited you to join circle {} on Opencircles platform. Join Opencircles today to be part of the revolutionized community of borrowers and lenders. Opencircles is currently available on google play store http://goo.gl/5KWXhx".format(member.user.first_name, member.user.last_name, circle.circle_name)
                sms_instance.sendsms(invite.phone_number,message)
            invite.is_sent = True
            invite.save()

    def deactivate_circle_member(self):
        loans = LoanApplication.objects.filter(is_approved=True, is_disbursed=True, is_fully_repaid=False).exclude(loan_tariff=None)
        for loan in loans:
            print(loan)
            member = loan.circle_member.member
            circle = loan.circle_member.circle
            loan_tariff = loan.loan_tariff
            if loan_tariff is None:
                loan_tariff = LoanTariff.objects.get(max_amount__gte=loan.amount,min_amount__lte=loan.amount,circle=circle)
            num_of_months = loan_tariff.num_of_months
            date_of_payment = loan.time_of_application.date() + relativedelta(months=num_of_months)
            today = datetime.datetime.now().date()
            if today > date_of_payment:
                title = "Circle {} account deactivation".format(circle.circle_name)
                message = "Your account has been deactivated due to late repayment of loan {}. Kindly repay your loan to continue saving, borrowing and earning interests from other circle members' loans.".format(loan.loan_code)
                CircleMember.objects.filter(circle=circle,member=member).update(is_active=False)
                fcm_instance = fcm_utils.Fcm()
                registration_id = member.device_token
                curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fcm_data = {"request_type":"SYSTEM_WARNING_MSG","title":title,"message":message,"time":today}
                fcm_instance.data_push("single", registration_id, fcm_data)
                fcm_data = {"request_type":"UPDATE_CIRCLE_MEMBER_STATUS", "phone_number":member.phone_number, "circle_acc_number":circle.circle_acc_number, 'is_active':False}
                registration_ids = fcm_instance.get_circle_members_token(circle,None)
                fcm_instance.data_push("multiple", registration_ids, fcm_data)

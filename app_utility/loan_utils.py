from __future__ import division

import math,uuid,threading
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Sum,Q

from loan.models import LoanApplication,GuarantorRequest,LoanTariff
from shares.models import IntraCircleShareTransaction,LockedShares,UnlockedShares
from wallet.models import RevenueStreams,Transactions
from circle.models import CircleMember
from member.models import Member

from shares.serializers import SharesTransactionSerializer
from wallet.serializers import WalletTransactionsSerializer

from app_utility import circle_utils,fcm_utils,general_utils,shares_utils,wallet_utils

class Loan():
    def validate_loan_amount(self,request,loan_amount,circle):
        circle_instance = circle_utils.Circle()
        circle_member_loan_limit = self.calculate_loan_limit(circle,request.user.member)
        print("circle member loan limit")
        print(circle_member_loan_limit)
        if loan_amount >= settings.MINIMUM_LOAN:
                if loan_amount <= circle_member_loan_limit:
                    return True,""
                return False,"The applied loan amount exceeds your loan limit"
        return False,"The allowed minimum loan is KES %s"%(settings.MINIMUM_LOAN)

    def validate_repayment_amount(self,amount,loan_amortization):
        max_repaid_amount = loan_amortization.total_repayment + math.ceil(loan_amortization.ending_balance)
        min_repaid_amount = loan_amortization.total_repayment
        if amount >= min_repaid_amount:
            if amount <= max_repaid_amount:
                return True,""
            return False,"Amount entered exceeds the current total repayable loan amount of KES {}".format(max_repaid_amount)
        return False,"The amount entered is less than this month allowed minimun repayment amount of KES{}".format(min_repaid_amount)

    def full_amortization_schedule(self,annual_interest,balance,num_of_months,date_time_approved):
        monthly_interest = annual_interest/(12*100)
        i = monthly_interest
        n = num_of_months
        repayment = balance * ((i * math.pow(1 + i, n)) / (math.pow(1 + i, n) - 1))
        temp_date = date_time_approved
        ending_balance = balance
        full_amortize =[]
        while ending_balance > 1:
            repayment_date = temp_date + relativedelta(months=1)
            fmt_date = repayment_date.strftime('%Y-%m-%d')
            temp_date = repayment_date
            starting_balance = ending_balance
            interest = starting_balance * monthly_interest
            principal = repayment - interest
            ending_balance = max(0, starting_balance - principal)
            total_repayment = math.ceil(float(format(repayment,'.2f')))
            data = {'repayment_date':fmt_date,'principal':round(principal,2),'interest':round(interest,2),'total_monthly_repayment':total_repayment,'ending_balance':round(ending_balance,2)}
            full_amortize.append(data)
        return full_amortize

    def amortization_schedule(self,annual_interest, balance, num_of_months, date_time_approved):
        monthly_interest = annual_interest/(12*100)
        i = monthly_interest
        n = num_of_months
        repayment = balance * ((i * math.pow(1 + i, n)) / (math.pow(1 + i, n) - 1))
        temp_date = date_time_approved
        repayment_date = temp_date + relativedelta(months=1)
        starting_balance = balance
        interest = starting_balance * monthly_interest
        principal = repayment - interest
        ending_balance = max(0, starting_balance - principal)
        print("Date: {0} Starting Balance: {1:.2f} principal:  {2:.2f} Interest: {3:.2f} Repayment: {4:.2f} Ending Balance: {5:.2F}".format(repayment_date, starting_balance, principal, interest, repayment,ending_balance))
        total_repayment = math.ceil(float(format(repayment,'.2f')))
        data = {"repayment_date":repayment_date,"starting_balance":round(starting_balance,2),"principal":round(principal,2),"interest":round(interest,2),"total_repayment":total_repayment,"ending_balance":round(ending_balance,2)}
        return data

    def get_total_guaranteed_amount(self,loan,shares):
        # loan = LoanApplication.objects.get(loan_code=loan_code)
        locked_shares = LockedShares.objects.filter(loan=loan).get(shares_transaction__shares=shares)
        num_of_shares = locked_shares.shares_transaction.num_of_shares
        guaranteed_amount = loan.amount - num_of_shares
        print(guaranteed_amount)
        return guaranteed_amount

    def get_remaining_guaranteed_amount(self,loan,shares):
        total_guaranteed_amount = self.get_total_guaranteed_amount(loan,shares)
        accepted_guaranteed_amount = GuarantorRequest.objects.filter(loan=loan,has_accepted=True).aggregate(total=Sum('num_of_shares'))
        guaranteed_amount = 0 if accepted_guaranteed_amount['total'] is None else accepted_guaranteed_amount['total']
        remaining_amount = total_guaranteed_amount - guaranteed_amount
        return remaining_amount

    def loan_repayment_reminder(self):
        today = datetime.now().date()
        loans = LoanApplication.objects.filter(is_fully_repaid=False,is_disbursed=True,is_approved=True)
        fcm_instance = fcm_utils.Fcm()
        for loan in loans:
            member,circle = loan.circle_member.member,loan.circle_member.circle
            days_to_send = [0,1,3,7]
            amortize_loan = loan.loan_amortization.filter()
            if amortize_loan.exists():
                latest_schedule = amortize_loan.latest('id')
                diff = today - latest_schedule.repayment_date
                delta = diff.days
                if delta in days_to_send:
                    fcm_instance = fcm_utils.Fcm()
                    title = "Circle {} loan repayment".format(circle.circle_name)
                    if delta == 0:
                        message = "You loan repayment of {} {} in circle {} is due today.Kindly make the payments before end of today to avoid penalties.".format(member.currency,latest_schedule.total_repayment,circle.circle_name)
                    else:
                        message = "Remember to make your loan repayment of {} {} in circle {} before {}".format(member.currency,latest_schedule.total_repayment,circle.circle_name,latest_schedule.repayment_date)
                    registration_id = member.device_token
                    fcm_instance.notification_push("single",registration_id,title,message)

    def unlock_guarantors_shares(self, guarantors, shares_desc):
        loan = guarantors[0].loan
        loan_member = loan.circle_member.member
        for guarantor in guarantors:
            try:
                general_instance = general_utils.General()
                created_objects = []
                circle_instance = circle_utils.Circle()
                circle, member = guarantor.circle_member.circle, guarantor.circle_member.member
                shares = guarantor.circle_member.shares.get()
                shares_transaction_code = general_instance.generate_unique_identifier('STU')
                shares_desc = "{} confirmed.Shares worth {} {} that were locked to guarantee loan {} of {} {} have been unlocked{}".format(shares_transaction_code, member.currency, guarantor.num_of_shares, loan.loan_code, loan_member.user.first_name, loan_member.user.last_name, shares_desc)
                locked_shares = LockedShares.objects.filter(loan=loan).get(shares_transaction__shares=shares)
                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="UNLOCKED",num_of_shares=guarantor.num_of_shares,transaction_desc=shares_desc,transaction_code=shares_transaction_code)
                created_objects.append(shares_transaction)
                unlocked_shares = UnlockedShares.objects.create(locked_shares=locked_shares, shares_transaction=shares_transaction)
                created_objects.append(unlocked_shares)
                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                loan_limit = self.calculate_loan_limit(circle,member)
                guarantor.unlocked = True
                guarantor.save()
                instance = fcm_utils.Fcm()
                fcm_data = {"request_type":"UNLOCK_SHARES", "shares_transaction":shares_transaction_serializer.data, "loan_limit":loan_limit}
                registration_id = member.device_token
                instance.data_push("single", registration_id, fcm_data)
                fcm_data = {"request_type":"DELETE_GUARANTEE_LOAN_REQUEST", "loan_code":guarantor.loan.loan_code}
                instance.data_push("single", registration_id, fcm_data)
                fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES", "circle_acc_number":circle.circle_acc_number, "phone_number":member.phone_number, "available_shares":fcm_available_shares}
                registration_id = instance.get_circle_members_token(circle, member)
                instance.data_push("multiple", registration_id, fcm_data)
            except Exception as e:
                print(str(e))
                general_utils.General().delete_created_objects(created_objects)

    def delete_expired_loan(self):
        today = datetime.now().date()
        loans = LoanApplication.objects.filter(is_approved=False, is_disbursed=False)
        expiry_days = [1,0]
        for loan in loans:
            loan_expiry_date = loan.time_of_application.date() + relativedelta(weeks=1)
            diff = loan_expiry_date - today
            delta = diff.days
            if delta in expiry_days:
                circle, member = loan.circle_member.circle, loan.circle_member.member
                fcm_instance = fcm_utils.Fcm()
                if delta == 1:
                    today = datetime.now()
                    today = today.strftime("%Y-%m-%d %H:%M:%S")
                    title = "Circle {} loan".format(circle.circle_name)
                    message = "Your loan of {} {} will be cancelled on {} due to few loan guarantors.".format(member.currency,loan.amount,loan_expiry_date)
                    fcm_data = {"request_type":"SYSTEM_WARNING_MSG","title":"Loan Cancellation","message":message,"time":today}
                    registration_id = member.device_token
                    fcm_instance.data_push("single",registration_id,fcm_data)
                else:
                    created_objects = []
                    try:
                        general_instance = general_utils.General()
                        amount = loan.amount
                        guarantors = loan.guarantor.filter(has_accepted=True)
                        shares_desc = " following cancellation of the loan."
                        self.unlock_guarantors_shares(guarantors,shares_desc)
                        shares = loan.circle_member.shares.get()
                        locked_shares = LockedShares.objects.filter(loan=loan).get(shares_transaction__shares=shares)
                        num_of_shares = locked_shares.shares_transaction.num_of_shares
                        shares_transaction_code = general_instance.generate_unique_identifier('STU')
                        shares_desc = "{} confirmed.Shares worth {} {} that were locked to guarantee your loan {} of {} {} have been unlocked following cancellation of loan.".format(shares_transaction_code, member.currency, num_of_shares, loan.loan_code, member.currency, loan.amount)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares, transaction_type="UNLOCKED", num_of_shares=num_of_shares, transaction_desc=shares_desc, transaction_code=shares_transaction_code)
                        created_objects.append(shares_transaction)
                        unlocked_shares = UnlockedShares.objects.create(locked_shares=locked_shares,shares_transaction=shares_transaction)
                        created_objects.append(unlocked_shares)
                        shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                        loan_limit = self.calculate_loan_limit(circle,member)
                        fcm_instance = fcm_utils.Fcm()
                        registration_id = member.device_token
                        fcm_data = {"request_type":"UNLOCK_SHARES","shares_transaction":shares_transaction_serializer.data,"loan_limit":loan_limit}
                        fcm_instance.data_push("single",registration_id,fcm_data)
                        fcm_data = {"request_type":"DECLINE_LOAN","loan_code":loan.loan_code}
                        fcm_instance.data_push("single",registration_id,fcm_data)
                        loan.delete()
                        self.update_loan_limit(circle,member)
                    except Exception as e:
                        print(str(e))
                        general_utils.General().delete_created_objects(created_objects)

    def calculate_total_paid_principal(self,loan):
        guaranteed = GuarantorRequest.objects.filter(loan=loan).aggregate(total=Sum('num_of_shares'))
        total_amortized = loan.loan_amortization.filter()
        interest = total_amortized.aggregate(total=Sum('interest'))
        total_paid = total_amortized.aggregate(total=Sum('loan_repayment__amount'))
        total_paid = 0 if total_paid['total'] is None else total_paid['total']
        principal = total_paid - interest['total']
        if principal >= guaranteed['total']:
            return True
        return False

    def share_loan_interest(self,loan):
        print(loan)
        print(type(loan))
        interest = loan.loan_amortization.filter().aggregate(total=Sum('interest'))
        interest = interest['total']
        print("total interest")
        print(interest)
        # interest for flemish
        time_transacted = datetime.now()
        general_instance = general_utils.General()
        flemish_revenue = (settings.INTEREST_SHARE/100)*interest
        print("flemish")
        print(flemish_revenue)
        guarantors_interest = 0
        fcm_instance = fcm_utils.Fcm()
        created_objects = []
        try:
            revenue = RevenueStreams.objects.create(stream_amount=flemish_revenue,stream_type="LOAN INTEREST",stream_code=loan.loan_code,time_of_transaction=time_transacted)
            created_objects.append(revenue)
            guarantors = GuarantorRequest.objects.filter(loan=loan,has_accepted=True)
            loan_user = loan.circle_member.member.user
            fcm_instance = fcm_utils.Fcm()
            guarantor_amount_disbursed = 0
            if guarantors.exists():
                # create model RevenueStreams
                guarantors_interest = (settings.GUARANTORS_INTEREST/100)*interest
                for guarantor in guarantors:
                    circle_member = guarantor.circle_member
                    circle, member = circle_member.circle, circle_member.member
                    ms = "guarantor {} with fraction {}".format(member.user.first_name,guarantor.fraction_guaranteed )
                    amount = float(guarantor.fraction_guaranteed * guarantors_interest)
                    amount_str = str(amount).split('.')
                    whole, dec = amount_str[0], amount_str[1]
                    if dec > 2:
                        dec = dec[0:2]
                        new_amount = whole + "." + dec
                        amount = float(new_amount)
                    wallet_instance = wallet_utils.Wallet()
                    transaction_code = general_instance.generate_unique_identifier('WTC')
                    wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) + amount
                    wallet_desc = "{} confirmed. You have received {} {} from circle {} as your guarantor interest of loan {} of {} {}.New wallet balance is {} {}.".format(transaction_code, member.currency, amount, circle.circle_name, loan.loan_code, loan_user.first_name, loan_user.last_name, member.currency, wallet_balance)
                    wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type="CREDIT", transaction_desc=wallet_desc, transaction_amount=amount, transaction_time=time_transacted, transacted_by=circle.circle_name, transaction_code=transaction_code)
                    created_objects.append(wallet_transaction)
                    guarantor_amount_disbursed = guarantor_amount_disbursed + amount
                    wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                    registration_id = member.device_token
                    fcm_data = {"request_type":"CREDIT_WALLET","wallet_transaction":wallet_transaction_serializer.data}
                    fcm_instance.data_push("single",registration_id,fcm_data)
            print("guarantee interest")
            print(guarantors_interest)
            circle_member_interest = interest - flemish_revenue - guarantors_interest
            print("circle_member interest")
            print(circle_member_interest)
            circle_members = CircleMember.objects.filter(member__time_registered__lt=loan.time_of_application,circle=loan.circle_member.circle).exclude(member=loan_user.member)
            member_amount_disbursed = 0
            for circle_member in circle_members:
                circle, member = circle_member.circle,circle_member.member
                shares = circle_member.shares.get()
                fraction = shares_utils.Shares().get_circle_member_shares_fraction(shares,loan.time_of_application,loan_user.member)
                ms = "circle member {} with fraction {}".format(member.user.first_name,fraction)
                amount = float(circle_member_interest * fraction)
                amount_str = str(amount).split('.')
                whole, dec = amount_str[0], amount_str[1]
                if dec > 2:
                    dec = dec[0:2]
                    new_amount = whole + "." + dec
                    amount = float(new_amount)
                wallet_instance = wallet_utils.Wallet()
                transaction_code = general_instance.generate_unique_identifier('WTC')
                wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) + amount
                wallet_desc = "{} confirmed. You have received {} {} from circle {} as interest of loan {}.New wallet balance {} {}.".format(transaction_code, member.currency,amount, circle.circle_name, loan.loan_code, member.currency, wallet_balance)
                wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type="CREDIT", transaction_desc=wallet_desc, transaction_amount=amount, transaction_time=time_transacted, transacted_by=circle.circle_name, transaction_code=transaction_code)
                created_objects.append(wallet_transaction)
                member_amount_disbursed += amount
                wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                registration_id = member.device_token
                fcm_data = {"request_type":"CREDIT_WALLET","wallet_transaction":wallet_transaction_serializer.data}
                fcm_instance.data_push("single",registration_id,fcm_data)
            rem = float(interest - (flemish_revenue + guarantor_amount_disbursed + member_amount_disbursed))
            print("Uncatered")
            print(rem)
            if rem != 0:
                revenue = RevenueStreams.objects.create(stream_amount=rem,stream_type="LOAN INTEREST",stream_code=loan.loan_code,time_of_transaction=time_transacted,extra_info="Uncatered for")
        except Exception as e:
            print(str(e))
            general_instance.delete_created_objects(created_objects)

    def send_guarantee_requests(self,loan_guarantors,member):
        loan = loan_guarantors[0].loan
        loan_tariff = loan.loan_tariff
        if loan_tariff is None:
            loan_tariff = LoanTariff.objects.get(circle=loan.circle_member.circle,max_amount__gte=loan.amount,min_amount__lte=loan.amount)
        annual_interest_rate = loan_tariff.monthly_interest_rate*12
        loan_amortization = self.full_amortization_schedule(annual_interest_rate, loan.amount, loan_tariff.num_of_months, datetime.now().date())[0]
        circle_instance = circle_utils.Circle()
        print(loan_amortization['interest'])
        interest = loan_amortization['interest'] * loan_tariff.num_of_months
        print(interest)
        guarantor_interest = settings.GUARANTORS_INTEREST/100
        print(guarantor_interest)
        guarantors_interest = guarantor_interest*interest
        threads = []
        for guarantor in loan_guarantors:
            guarantor_member, circle = guarantor.circle_member.member, guarantor.circle_member.circle
            loan = guarantor.loan
            guarantor_available_shares = circle_instance.get_guarantor_available_shares(circle,guarantor_member)
            estimated_earning = guarantors_interest*guarantor.fraction_guaranteed
            print("estimated earning")
            print(estimated_earning)
            rating = self.calculate_circle_member_loan_rating(member)
            print("rating")
            print(rating)
            fcm_instance = fcm_utils.Fcm()
            fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":guarantor_member.phone_number,"available_shares":guarantor_available_shares}
            registration_ids = fcm_instance.get_circle_members_token(circle,guarantor_member)
            fcm_instance.data_push("multiple",registration_ids,fcm_data)
            # t1 = threading.Thread(target=fcm_instance.data_push, args=("multiple",registration_ids,fcm_data))
            # t1.start()
            # threads.append(t1)
            fcm_data = {"request_type":"GUARANTEE_LOAN_REQUEST","phone_number":member.phone_number,"circle_acc_number":circle.circle_acc_number,"loan_code":loan.loan_code,"amount":guarantor.num_of_shares,"num_of_months":loan_tariff.num_of_months,"rating":rating,"estimated_earning":estimated_earning}
            registration_id = guarantor_member.device_token
            fcm_instance.data_push("single",registration_id,fcm_data)
            # t2 = threading.Thread(target=fcm_instance.data_push,args=("single",registration_id,fcm_data))
            # t2.start()
            # threads.append(t2)
            # title = circle.circle_name
            # adverb = "her" if member.gender == "F" or member.gender == "Female" else "him"
            # message = "%s %s has requested you to guarantee %s KES %s "%(member.user.first_name,member.user.last_name,adverb,guarantor.num_of_shares)
            # instance.notification_push("single",registration_id,title,message)
        # for t in threads:
        #     t.join()

    def calculate_loan_limit(self,circle,member):
        print(member.user.first_name)
        circle_instance = circle_utils.Circle()
        available_shares = circle_instance.get_available_circle_member_shares(circle,member)
        print(available_shares)
        total_shares = circle_instance.get_available_circle_shares(circle)
        print(total_shares)
        actual_available_shares = total_shares - available_shares
        if total_shares > 0:
            loan_limit = int(math.floor(available_shares + ((available_shares/total_shares)*actual_available_shares)))
            if loan_limit >= settings.MAXIMUM_CIRCLE_SHARES:
                return settings.MAXIMUM_CIRCLE_SHARES
            print("loan_limit")
            print(loan_limit)
            return loan_limit
        return available_shares

    def update_loan_limit(self,circle,member):
        fcm_instance = fcm_utils.Fcm()
        registration_ids = fcm_instance.get_circle_members_token(circle,member)
        if len(registration_ids):
            threads = []
            for reg_id in registration_ids:
                try:
                    member = Member.objects.get(device_token=reg_id)
                    print(member.user.first_name)
                    loan_limit = self.calculate_loan_limit(circle,member)
                    print("loan limit")
                    print(loan_limit)
                    fcm_data = {"request_type":"UPDATE_LOAN_LIMIT","circle_acc_number":circle.circle_acc_number,"loan_limit":loan_limit}
                    fcm_instance.data_push("single",reg_id,fcm_data)
                    # t = threading.Thread(target=fcm_instance.data_push, args=("single",reg_id,fcm_data))
                    # t.start()
                    # threads.append(t)
                except Member.DoesNotExist:
                    continue
            # for t in threads:
            #     t.join()

    def set_loan_rating(self,loan):
        today = datetime.now().date()
        repayment_date = loan.loan_amortization.get().repayment_date
        diff = today - repayment_date
        delta = diff.days
        if delta <= 0:
            return 5
        elif delta > 0 and delta <= 7:
            return 4
        elif delta > 7 and delta <= 14:
            return 3
        elif delta > 14 and delta <= 21:
            return 2
        elif delta > 21 and delta <= 28:
            return 1
        else:
            return 0

    def calculate_circle_member_loan_rating(self,member):
        loans = LoanApplication.objects.filter(circle_member__member=member,is_disbursed=True,is_approved=True).exclude(time_of_last_payment=None)
        if loans.exists():
            loans = loans.exclude(loan_amortization__loan_repayment__rating=None)
            rating = loans.aggregate(total=Sum('loan_amortization__loan_repayment__rating'))
            repayment_count = loans.values_list('loan_amortization__loan_repayment__rating').count()
            avg_rating = rating['total']/repayment_count
            return round(avg_rating,2)
        return -1

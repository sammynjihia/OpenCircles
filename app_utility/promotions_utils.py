from wallet.models import ReferralFee, Transactions
from wallet.serializers import WalletTransactionsSerializer
from member.models import Member
from django.db import transaction
from . import wallet_utils, general_utils, fcm_utils
import datetime

class Promotions():
    def referral_programme(self, is_invited, amount):
        try:
            member = Member.objects.get(phone_number=is_invited.phone_number)
            try:
                referral_fee = ReferralFee.objects.create(member=member,
                                                          circle=is_invited.invited_by.circle,
                                                          invited_by=is_invited.invited_by.member,
                                                          amount=amount)
                try:
                    wallet_instance = wallet_utils.Wallet()
                    general_instance = general_utils.General()
                    sender = Member.objects.get(phone_number="+254795891656")
                    if wallet_instance.calculate_wallet_balance(sender.wallet) >= amount:
                        recipient = referral_fee.invited_by
                        sender_wallet = sender.wallet
                        recipient_wallet = recipient.wallet
                        suffix = general_instance.generate_unique_identifier('')
                        sender_transaction_code = 'WTRD' + suffix
                        recipient_transaction_code = 'WTRC' + suffix
                        sender_wallet_balance = wallet_instance.calculate_wallet_balance(sender_wallet) - amount
                        recipient_wallet_balance = wallet_instance.calculate_wallet_balance(recipient_wallet) + amount
                        sender_desc = "{} confirmed.You have sent {} {} to {} {} on behalf of opencircles " \
                                      "referral programme.New wallet balance is {} {}.".format(sender_transaction_code,
                                                                                               sender.currency,
                                                                                               amount,
                                                                                               recipient.user.first_name,
                                                                                               recipient.user.last_name,
                                                                                               sender.currency,
                                                                                               sender_wallet_balance)
                        recipient_desc = "{} confirmed.You have received {} {} from opencircles referral programme." \
                                         "New wallet balance is {} {}. {} has joined {}." \
                                         "When you invite a friend to join your circle on Opencircles," \
                                         " your wallet is credited with {} {}.".format(recipient_transaction_code,
                                                                                      recipient.currency, amount,
                                                                                      recipient.currency,
                                                                                      recipient_wallet_balance,
                                                                                      member.phone_number,
                                                                                      is_invited.invited_by.circle.circle_name,
                                                                                      recipient.currency,
                                                                                      amount)
                        try:
                            with transaction.atomic():
                                sender_transaction = Transactions.objects.create(wallet= sender_wallet,
                                                                                 transaction_type="DEBIT",
                                                                                 transaction_desc=sender_desc,
                                                                                 transaction_amount=amount,
                                                                                 transaction_time=datetime.datetime.now(),
                                                                                 recipient=recipient.phone_number,
                                                                                 transaction_code=sender_transaction_code,
                                                                                 source="referral programme")
                                recipient_transaction = Transactions.objects.create(wallet = recipient_wallet,
                                                                                    transaction_type="CREDIT",
                                                                                    transaction_desc=recipient_desc,
                                                                                    transaction_amount=amount,
                                                                                    transacted_by=sender.phone_number,
                                                                                    transaction_time=datetime.datetime.now(),
                                                                                    transaction_code=recipient_transaction_code,
                                                                                    source="referral programme")
                                sender_wallet_transaction = WalletTransactionsSerializer(sender_transaction)
                                recipient_wallet_transaction = WalletTransactionsSerializer(recipient_transaction)
                                fcm_instance = fcm_utils.Fcm()
                                sender_fcm_data = {"request_type":"WALLET_TO_WALLET_TRANSACTION",
                                                   "wallet_transaction":sender_wallet_transaction.data}
                                recipient_fcm_data = {"request_type":"WALLET_TO_WALLET_TRANSACTION",
                                                       "wallet_transaction":recipient_wallet_transaction.data}
                                is_invited.delete()
                                try:
                                    fcm_instance.data_push("single", sender.device_token, sender_fcm_data)
                                    fcm_instance.data_push("single", recipient.device_token, recipient_fcm_data)
                                except Exception as e:
                                    print(str(e))
                                    print("fcm is unavailable")
                        except Exception as e:
                            print(str(e))
                            transaction.rollback()
                            referral_fee.extra_info = "Error when saving transactions to database"
                            referral_fee.is_disbursed = False
                            referral_fee.save()
                    else:
                        referral_fee.extra_info = "Insufficient balance in debitor account"
                        referral_fee.is_disbursed = False
                        referral_fee.save()
                except Member.DoesNotExist:
                    referral_fee.extra_info = "Debitor does not exist"
                    referral_fee.is_disbursed = False
                    referral_fee.save()
            except Exception as e:
                print(str(e))
        except Member.DoesNotExist:
            print(str(e))
            print("Member does not exist")

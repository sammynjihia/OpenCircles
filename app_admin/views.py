import json
import datetime

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse

from . import members_utils, circles_utils, loan_utils, revenue_streams_utils, shares_utils, transactions_utils, contacts_utils
from . import chat_utils
from circle.models import Circle
from member.models import Member
from wallet.models import Transactions, AdminMpesaTransaction_logs,  ReferralFee, AirtimePurchaseLog

from wallet.serializers import WalletTransactionsSerializer

from app_utility import sms_utils, wallet_utils, fcm_utils, general_utils


# Create your views here.

def create_admin(request):
    pass

def lock_admin_acc(request):
    pass

def login_page(request):
    return render(request, 'app_admin/login_page.html', {})

def login_admin(request):
    password = request.POST.get('password')
    username = request.POST.get('username')
    return_data = {}
    user = User.objects.get(username=username, is_superuser=True, is_staff=True)

    if user.is_active is False:
        return_data['STATUS'] = '0'
        return_data['MESSAGE'] = 'Account has been locked. Contact admin to unlock your account.'
    else:
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return_data['STATUS'] = '1'
            return_data['URL'] = 'home'
        else:
            return_data['STATUS'] = '0'
            return_data['MESSAGE'] = 'Invalid credentials.'

    return HttpResponse(
        json.dumps(return_data),
        content_type="application/json"
    )

@login_required(login_url='app_admin:login_page')
def logout_admin(request):
    logout(request)
    return HttpResponse(
        json.dumps({'status': 1, 'URL': 'login_page'}),
        content_type="application/json"
    )

@login_required(login_url='app_admin:login_page')
def home_page(request):
    mpesa_c2b =transactions_utils.TransactionUtils.get_transactions_by_day_and_source(datetime.datetime.today(),
                                                                                      'MPESA C2B')
    mpesa_c2b_total = 0.00
    mpesa_b2c =transactions_utils.TransactionUtils.get_transactions_by_day_and_source(datetime.datetime.today(),
                                                                                      'MPESA B2C')
    mpesa_b2c_total = 0.00
    mpesa_b2b = transactions_utils.TransactionUtils.get_transactions_by_day_and_source(datetime.datetime.today(),
                                                                                       'MPESA B2B')
    mpesa_b2b_total = 0.00

    if mpesa_c2b is not None:
        mpesa_c2b_total = mpesa_c2b['total_amount']

    if mpesa_b2c is not None:
        mpesa_b2c_total = mpesa_b2c['total_amount']

    if mpesa_b2b is not None:
        mpesa_b2b_total = mpesa_b2b['total_amount']

    context = {
        'member': {
            'total_members': members_utils.MemberUtils.get_num_of_members(),
            'registered_today': members_utils.MemberUtils.get_num_of_members_registered__by_day()
        },
        'circle': {
            'num_of_circles': circles_utils.CircleUtils.get_num_of_circles(),
            'num_of_active_circles': circles_utils.CircleUtils.get_num_of_active_circles(),
            'num_of_circles_created_today': circles_utils.CircleUtils.get_num_of_circles_registered__by_day()
        },
        'loan_application': {
            'total_loans_applied_today': sum([x[0] for x in
                                              loan_utils.LoanUtils.get_loan_application_by_date().values_list('amount')]),

            'num_of_loans_today': loan_utils.LoanUtils.get_loan_application_by_date().count(),
            'amount_approved_today': sum([x[0] for x in
                                          loan_utils.LoanUtils.get_loan_application_by_date()
                                         .filter(is_approved=True, is_disbursed=True)
                                         .values_list('amount')]),
            'amount_pending_approval_today': sum([x[0] for x in
                                                  loan_utils.LoanUtils.get_loan_application_by_date()
                                                 .filter(is_approved=False, is_disbursed=False)
                                                 .values_list('amount')]),
        },
        'loan_repayment': {
            'total_loan_repaid_today': sum([x[0] for x in loan_utils.LoanUtils.get_loan_repayment_by_date().values_list(
                                                  'amount')]),
            'num_of_repayments': loan_utils.LoanUtils.get_loan_repayment_by_date().count(),
            'revenue': sum([x[0] for x in revenue_streams_utils.RevenueStreamsUtils.get_revenue_streams_by_date()
                    .filter(stream_type__icontains='LOAN')
                    .values_list('stream_amount')])
        },
        'shares': {
            'total_withdrawals_today': sum([x[0] for x in shares_utils.SharesUtils.get_shares_withdrawal_by_date()
                                .values_list('num_of_shares')]),
            'num_of_withdrawals': shares_utils.SharesUtils.get_shares_withdrawal_by_date().count(),
            'revenue': sum([x[0] for x in revenue_streams_utils.RevenueStreamsUtils.get_revenue_streams_by_date()
                           .filter(stream_type__icontains='SHARES')
                           .values_list('stream_amount')]),
            'available_shares': shares_utils.SharesUtils.get_total_available_shares()
        },
        'wallet_transactions': {
            'mpesa_c2b': mpesa_c2b_total,
            'mpesa_b2c': mpesa_b2c_total,
            'mpesa_b2b': mpesa_b2b_total,
            'wallet_balance': transactions_utils.TransactionUtils.get_total_wallet_balance(),
        },
        'contacts': {
            'total': contacts_utils.ContactsUtils.get_num_of_all_contacts(),
            'non_invited': contacts_utils.ContactsUtils.get_num_of_all_non_invited_contact(),
            'invited': contacts_utils.ContactsUtils.get_num_of_all_invited_contact()
        }
    }
    return render(request, 'app_admin/base_dashboard.html', context)

@login_required(login_url='app_admin:login_page')
def contact_list(request, offset=0):
    offset = int(offset)
    contacts_obj = contacts_utils.ContactsUtils.get_contacts_list()

    is_at_end = False
    contacts = None
    try:
        if (offset+100) < contacts_obj.count() - 1:
            contacts = contacts_obj[offset:offset+100]
        else:
            is_at_end = True
            contacts = contacts_obj[offset: contacts_obj.count()]
    except IndexError as exp:
        is_at_end = True
        contacts = contacts_obj[offset: contacts_obj.count()]
    print(offset)
    context = {
        'contacts': contacts,
        'members_from_contacts': '',
        'none_members': '',
        'is_at_top': True if offset == 0 else False,
        'previous_offset': offset - 100,
        'current_offset': offset,
        'next_offset': offset+100,
        'is_at_end': is_at_end,
        'invited': contacts_utils.ContactsUtils.get_num_of_all_invited_contact(),
        'non_invited': contacts_utils.ContactsUtils.get_num_of_all_non_invited_contact()
    }
    return render(request, 'app_admin/contacts_list.html', context)

@login_required(login_url='app_admin:login_page')
def members_page(request, offset=0):
    members_list = members_utils.MemberUtils.get_all_members()
    offset = int(offset)
    is_at_end = False
    members = None
    try:
        if (offset + 100) < members_list.count() - 1:
            members = members_list[offset:offset + 100]
        else:
            is_at_end = True
            members = members_list[offset: members_list.count()]
    except IndexError as exp:
        is_at_end = True
        members = members_list[offset: members_list.count()]

    context = {
        'members': members,
        'is_at_top': True if offset == 0 else False,
        'previous_offset': offset - 100,
        'current_offset': offset,
        'next_offset': offset+100,
        'is_at_end': is_at_end,
    }
    return render(request, 'app_admin/members.html', context)

@login_required(login_url='app_admin:login_page')
def search_for_member(request):
    search_val = request.POST.get('search_val')
    members_obj = members_utils.MemberUtils.search_for_member(search_val)
    members_list = []
    for obj in members_obj:
        members_list.append(
            {
                'id': obj.id,
                'name': "{} {} {}".format(obj.user.first_name, obj.user.last_name, obj.other_name),
                'national_id': obj.national_id,
                'phone_number': obj.phone_number,
                'email': obj.user.email,
                'gender': obj.gender,
                'date_of_birth': obj.date_of_birth.strftime('%d-%b-%Y')
            }
        )
    return HttpResponse(json.dumps(members_list))

@login_required(login_url='app_admin:login_page')
def members_reg_analysis(request):
    start_date = None
    end_date = None
    if request.method == 'POST':
        start_date = datetime.datetime.strptime(request.POST.get('start_date_val'), '%Y-%m-%d')
        end_date = datetime.datetime.strptime(request.POST.get('end_date_val'), '%Y-%m-%d')
    context = members_utils.MemberUtils.get_daily_registrations_count(start_date, end_date)
    return render(request, 'app_admin/member_reg_analysis.html', context)

@login_required(login_url='app_admin:login_page')
def view_member_details(request, member_id):
    request.session['member_id'] = member_id
    member = members_utils.MemberUtils.get_member_from_id(member_id)
    image_exists = False
    try:
        member.passport_image.url
        image_exists = True
    except:
        pass

    context = {
        'image_exists': image_exists,
        'member': member,
        'next_of_kin': members_utils.MemberUtils.get_next_of_kin(member),
        'circles': circles_utils.CircleUtils.get_circles_by_member(member),
        'transactions': transactions_utils.TransactionUtils.get_wallet_transaction_by_member(member)[:100],
        'loans': loan_utils.LoanUtils.get_loans_by_member(member)
    }
    return render(request, 'app_admin/member_details.html', context)

@login_required(login_url='app_admin:login_page')
def wallet_transactions(request, offset=0):
    trx_list = transactions_utils.TransactionUtils.get_days_wallet_transactions()
    offset = int(offset)
    is_at_end = False
    transactions = None
    try:
        if (offset + 100) < trx_list.count() - 1:
            transactions = trx_list[offset:offset + 100]
        else:
            is_at_end = True
            transactions = trx_list[offset: trx_list.count()]
    except IndexError as exp:
        is_at_end = True
        transactions = trx_list[offset: trx_list.count()]

    context = {
        'transactions': transactions,
        'is_at_top': True if offset == 0 else False,
        'previous_offset': offset - 100,
        'current_offset': offset,
        'next_offset': offset + 100,
        'is_at_end': is_at_end,
    }
    return render(request, 'app_admin/wallet_transactions_list.html', context)

@login_required(login_url='app_admin:login_page')
def search_for_transaction(request):
    transactions = []
    search_val = request.POST.get('search_val').strip()
    trx_objs = transactions_utils.TransactionUtils.search_wallet_transactions(search_val)
    for obj in trx_objs:
        sender = obj.transacted_by
        recipient = obj.transacted_by

        if sender.upper() == 'SELF':
            sender = "{} {} {}".format(obj.wallet.member.user.first_name, obj.wallet.member.user.last_name,
                                       obj.wallet.member.other_name)

        if recipient.upper() == 'SELF':
            recipient = "{} {} {}".format(obj.wallet.member.user.first_name, obj.wallet.member.user.last_name,
                                       obj.wallet.member.other_name)

        transactions.append({
            'id': obj.id,
            'transaction_code': obj.transaction_code,
            'amount': obj.transaction_amount,
            'sender': sender,
            'recipient': recipient,
            'time_of_transaction': obj.transaction_time.strftime('%d-%b-%Y %I-%M-%S %p'),
            'transaction_type': obj.transaction_type,
            'source': obj.source
        })
    return HttpResponse(json.dumps(transactions))

@login_required(login_url='app_admin:login_page')
def view_transaction_details(request, transaction_id):
    request.session['transaction_id'] = transaction_id
    trx = transactions_utils.TransactionUtils.get_transaction_by_id(transaction_id)
    context = {
        'transaction': trx,
        'current_balance': transactions_utils.TransactionUtils.get_wallet_balance_wallet_id(trx.wallet.id)
    }
    return render(request, 'app_admin/wallet_transaction.html', context)

@login_required(login_url='app_admin:login_page')
def mpesa_transactions(request, offset=0):
    mpesa_trx_obj = transactions_utils.TransactionUtils.get_mpesa_transactions_log()
    mpesa_trx_list = []

    for obj in mpesa_trx_obj:
        amount = 0
        try:
            if not obj.is_manually_committed:
                res_json = json.loads(obj.Response.strip())
            if obj.TransactionType.strip() == 'C2B':
                if obj.is_manually_committed:
                    amount = Transactions.objects.get(transaction_code=obj.TransactioID).transaction_amount
                else:
                    amount = res_json['TransAmount']
            elif obj.TransactionType.strip() == 'B2C' or obj.TransactionType.strip() == 'B2B':
                res_params = res_json['Result']['ResultParameters']['ResultParameter']
                for param in res_params:
                    if param['Key'] == 'TransactionAmount':
                        amount = param['Value']
                        break
                    if param['Key'] == 'Amount':
                        amount = param['Value']
                        break
        except Exception as e:
            print(str(e))
            pass

        mpesa_trx_list.append({
            'transaction_code': obj.TransactioID,
            'is_committed': obj.is_committed,
            'type': obj.TransactionType,
            'time': obj.transaction_time,
            'amount': amount,
            'response': obj.Response
        })

    transactions = None

    offset = int(offset)
    is_at_end = False
    transactions = None
    try:
        if (offset + 100) < len(mpesa_trx_list) - 1:
            transactions = mpesa_trx_list[offset:offset + 100]
        else:
            is_at_end = True
            transactions = mpesa_trx_list[offset: len(mpesa_trx_list)]
    except IndexError as exp:
        is_at_end = True
        transactions = mpesa_trx_list[offset: len(mpesa_trx_list)]

    context = {
        'transactions': transactions,
        'is_at_top': True if offset == 0 else False,
        'previous_offset': offset - 100,
        'current_offset': offset,
        'next_offset': offset + 100,
        'is_at_end': is_at_end,
    }
    return render(request, 'app_admin/mpesa_transactions.html', context)

@login_required(login_url='app_admin:login_page')
def view_mpesa_transaction(request, transaction_code):
    context = {
        'mpesa_transaction': transactions_utils.TransactionUtils.get_mpesa_transaction_by_transaction_code(transaction_code),
        'transaction': transactions_utils.TransactionUtils.get_transaction_by_transaction_code(transaction_code)
    }
    return render(request, 'app_admin/mpesa_transaction.html', context)

@login_required(login_url='app_admin:login_page')
def commit_mpesa_transaction(request):
    transaction_code = request.POST.get('transaction_code')
    mpesa_transaction = transactions_utils.TransactionUtils.get_mpesa_transaction_by_transaction_code(transaction_code)
    has_been_committed = transactions_utils.TransactionUtils.do_mpesa_wallet_reconciliation_reconciliation(mpesa_transaction)

    context = {
        'mpesa_transaction': transactions_utils.TransactionUtils.get_mpesa_transaction_by_transaction_code(transaction_code),
        'transaction': transactions_utils.TransactionUtils.get_transaction_by_transaction_code(transaction_code)
    }
    return render(request, 'app_admin/mpesa_transaction.html', context)

@login_required(login_url='app_admin:login_page')
def search_for_mpesa_transaction(request):
    if request.method == 'POST':
        transaction_code = request.POST.get('transaction_code').strip()
        start_date_val = request.POST.get('start_date_val').strip()
        end_date_val = request.POST.get('end_date_val').strip()

        if len(transaction_code) == 0:
            transaction_code = None
        start_date = None

        if start_date_val is not None:
            try:
                start_date = datetime.datetime.strptime(start_date_val, '%Y-%m-%d')
            except Exception as exp:
                start_date = None

        end_date = None
        if end_date_val is not None:
            try:
                end_date = datetime.datetime.strptime(end_date_val, '%Y-%m-%d')
            except Exception as exp:
                end_date = None

        mpesa_trx_obj = transactions_utils.TransactionUtils.search_for_mpesa_transaction(transaction_code, start_date,
                                                                                      end_date)
    else:
        mpesa_trx_obj = transactions_utils.TransactionUtils.get_mpesa_transactions_log()

    if mpesa_trx_obj is None:
        return render(request, 'app_admin/mpesa_transactions.html', {})

    mpesa_trx_list = []

    for obj in mpesa_trx_obj:
        amount = 0
        try:
            res_json = json.loads(obj.Response.strip())
            if obj.TransactionType.strip() == 'C2B':
                amount = res_json['TransAmount']
            elif obj.TransactionType.strip() == 'B2C':
                res_params = res_json['Result']['ResultParameters']['ResultParameter']
                for param in res_params:
                    if param['Key'] == 'TransactionAmount':
                        amount = param['Value']
                        break
        except Exception as e:
            print(str(e))
            pass

        mpesa_trx_list.append({
            'transaction_code': obj.TransactioID,
            'is_committed': obj.is_committed,
            'type': obj.TransactionType,
            'time': obj.transaction_time,
            'amount': amount,
            'response': obj.Response
        })

    context = {
        'transactions': mpesa_trx_list
    }
    return render(request, 'app_admin/mpesa_transactions.html', context)

@login_required(login_url='app_admin:login_page')
def transactions_days_analytics(request):
    source = ''
    date = datetime.datetime.today()
    if request.method == 'POST':
        search_date = request.POST.get('search_date_val')
        date = datetime.datetime.strptime(search_date, '%Y-%m-%d')
        source = request.POST.get('source')

    trx = transactions_utils.TransactionUtils.get_transactions_by_day_and_source(date, source)
    return render(request, 'app_admin/wallet_transactions_analytics.html', trx)

@login_required(login_url='app_admin:login_page')
def financial_stmt(request):
    context = {
        'wallet_balance': transactions_utils.TransactionUtils.get_total_wallet_balance(),
        'available_shares': shares_utils.SharesUtils.get_total_available_shares()
    }
    return render(request, 'app_admin/financial_stmt.html', context)

@login_required(login_url='app_admin:login_page')
def cash_flow(request):
    context = {

    }
    return render(request, 'app_admin/cash_flow.html')

@login_required(login_url='app_admin:login_page')
def revenue(request):
    context = {}
    return render(request, 'app_admin/revenue.html')

@login_required(login_url='app_admin:login_page')
def expenditure(request):
    context = {}
    return render(request, 'app_admin/expenditure.html')

@login_required(login_url='app_admin:login_page')
def balance_sheet(request):
    context = {}
    return render(request, 'app_admin/balance_sheet.html', context)

@login_required(login_url='app_admin:login_page')
def loan_applications(request, offset=0):
    loans_list = loan_utils.LoanUtils.get_loans_list()
    offset = int(offset)
    is_at_end = False
    loans = None
    try:
        if (offset + 100) < loans_list.count() - 1:
            loans = loans_list[offset:offset + 100]
        else:
            is_at_end = True
            loans = loans_list[offset: loans_list.count()]
    except IndexError as exp:
        is_at_end = True
        loans = loans_list[offset: loans_list.count()]
    context = {
        'loans': loans,
        'is_at_top': True if offset == 0 else False,
        'previous_offset': offset - 100,
        'current_offset': offset,
        'next_offset': offset + 100,
        'is_at_end': is_at_end,
    }
    template = 'app_admin/loan_applications_list.html'
    return render(request, template, context)

@login_required(login_url='app_admin:login_page')
def search_for_loan_applications(request):
    loans_list = []
    search_val = request.POST.get('search_val')
    loans_objs = loan_utils.LoanUtils.search_for_loan(search_val)

    for obj in loans_objs:
        member = obj.circle_member.member
        need_guarantors = 'NO'

        if loan_utils.LoanUtils.loan_need_guarantors(obj.loan_code):
            need_guarantors = 'YES'

        loans_list.append({
            'loan_code': obj.loan_code,
            'circle': obj.circle_member.circle.circle_name,
            'applicant': "{}({} {})".format(member.phone_number, member.user.first_name, member.user.last_name),
            'time': obj.time_of_application.strftime('%d-%b-%Y %I-%M-%S %p'),
            'amount': obj.amount,
            'need_guarantors': need_guarantors,
            'is_approved': 'YES' if obj.is_approved else 'NO',
            'is_disbursed': 'YES' if obj.is_disbursed else 'NO',
            'is_fully_repaid': 'YES' if obj.is_fully_repaid else 'NO'
        })
    return HttpResponse(json.dumps(loans_list))

@login_required(login_url='app_admin:login_page')
def view_loan_application_details(request, loan_code):
    loan = loan_utils.LoanUtils.get_loan_by_loan_code(loan_code)
    guarantors = loan_utils.LoanUtils.get_loan_guarantors(loan)
    loan_repayment = loan_utils.LoanUtils.get_loan_repayment(loan)
    context = {
        'loan': loan,
        'guarantors': guarantors,
        'need_guarantors': guarantors.exists(),
        'loan_repayment_exists': loan_repayment.exists(),
        'loan_repayment': loan_repayment,
        'associated_transaction': transactions_utils.TransactionUtils.get_wallet_trx_by_loan(loan)
    }
    return render(request, 'app_admin/loan_application.html', context)

@login_required(login_url='app_admin:login_page')
def get_num_of_chats(request):
    num_of_pending_chats = chat_utils.ChatUtils.get_num_of_pending_chats()
    return HttpResponse(json.dumps({'num_of_chats': num_of_pending_chats}))

@login_required(login_url='app_admin:login_page')
def chats_list(request):
    chat_objs =  chat_utils.ChatUtils.get_pending_chats()
    chats = []
    for obj in chat_objs:
        url_exist = False
        image_url = ''
        try:
            image_url = obj.owner.passport_image.url
            url_exist = True
            if len(image_url) == 0:
                url_exist = False
        except:
            url_exist = False
        print("{} ".format(obj.owner.user.first_name))
        chats.append({'id': obj.id,
                      'name': u"{} {}".format(obj.owner.user.first_name, obj.owner.user.last_name),
                      'time_chat_sent': obj.time_chat_sent,
                      'body': obj.body,
                      'has_been_responded_to':obj.has_been_responded_to,
                      'url_exist': url_exist,
                      'image_url': image_url
                    })
    context = {
        'chats':chats
    }
    return render(request, 'app_admin/chats.html', context)

@login_required(login_url='app_admin:login_page')
def reply_to_chat(request):
    chat_id = request.POST.get('chat_id')
    body = request.POST.get('body')
    reply_chat = chat_utils.ChatUtils.reply_to_chat(chat_id, body)
    response = {
        'status': 1 if reply_chat else 0,
        'message': 'Sent' if reply_chat else 'Failed',
    }
    return HttpResponse(json.dumps(response))

@login_required(login_url='app_admin:login_page')
def cancel_chat(request):
    chat_id = request.POST.get('chat_id')
    is_canceled = chat_utils.ChatUtils.cancel_chat(chat_id)
    response = {
        'status': 1 if is_canceled else 0,
        'message': 'Canceled' if is_canceled else 'Failed',
    }
    return HttpResponse(json.dumps(response))

@login_required(login_url='app_admin:login_page')
def new_chat(request):
    print(request.POST)
    if request.method != 'POST':
        context = {
            'circles': circles_utils.CircleUtils.get_all_circles(),
            'members': members_utils.MemberUtils.get_all_members()
        }
        return render(request, 'app_admin/new_chat.html', context)
    else:
        message = request.POST.get('message')
        recipient_type = request.POST.get('recipient_type')
        recipient = request.POST.get('recipient')
        message_channel = int(request.POST.get('message_channel'))
        if recipient_type == 'circle':
            circle = Circle.objects.get(circle_name__icontains=recipient)
            if chat_utils.ChatUtils.send_chat_to_circle_members(message, circle, message_channel):
                return HttpResponse(json.dumps({'status': 1, 'message': 'Message sent successfully'}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': 'An error occurred.'}))
        elif recipient_type == 'member':
            member = Member.objects.get(phone_number=recipient)
            if chat_utils.ChatUtils.send_single_chat(message, member, message_channel):
                return HttpResponse(json.dumps({'status': 1, 'message': 'Message sent successfully'}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': 'An error occurred.'}))
        elif recipient_type == 'all':
            if chat_utils.ChatUtils.send_chat_to_all_members(message,message_channel):
                return HttpResponse(json.dumps({'status': 1, 'message': 'Message sent successfully'}))
            else:
                return HttpResponse(json.dumps({'status': 0, 'message': 'An error occurred.'}))

@login_required(login_url='app_admin:login_page')
def search_for_chats(request):
    search_val = request.POST.get('search_val')
    chat_objs = chat_utils.ChatUtils.search_for_chats(search_val)
    chats_list = []
    for obj in chat_objs:
        chats_list.append({
            'id': obj.id,
            'body': obj.body,
            'time_chat_sent': obj.time_chat_sent.strftime('%Y-%m-%d %H-%m-%s'),
            'member_name': "{} {} {}".format(obj.owner.user.first_name, obj.owner.user.last_name, obj.owner.other_name),
            'image_url': "{}".format(obj.owner.passport_image.url),
            'has_been_responded_to': 1 if obj.has_been_responded_to else 0,
        })

    return HttpResponse(json.dumps(chats_list))

@login_required(login_url='app_admin:login_page')
def circles_list(request):
    circle_objs = circles_utils.CircleUtils.get_all_circles()
    lis_of_cirlces = []
    for obj in circle_objs:
        lis_of_cirlces.append({
            'id': obj.id,
            'circle_name': obj.circle_name,
            'circle_acc_number': obj.circle_acc_number,
            'circle_type': obj.circle_type,
            'time_initiated': obj.time_initiated,
            'initiated_by': "{} {}".format(obj.initiated_by.user.first_name, obj.initiated_by.user.last_name),
            'minimum_share': obj.minimum_share,
            'number_of_members': circles_utils.CircleUtils.get_num_of_circle_members(obj),
            'total_deposits': shares_utils.SharesUtils.get_total_shares_deposit(obj),
            'total_withdrawals': shares_utils.SharesUtils.get_total_withdrawals(obj),
            'locked_shares': shares_utils.SharesUtils.get_circle_locked_shares(obj),
            'available_shares': shares_utils.SharesUtils.get_circles_available_shares(obj),
        })
    return render(request, 'app_admin/circles_list.html', {'circles': lis_of_cirlces})

@login_required(login_url='app_admin:login_page')
def view_circle_details(request, circle_id):
    circle = circles_utils.CircleUtils.get_circle_by_id(circle_id)
    members_count = circles_utils.CircleUtils.get_count_of_circle_members(circle)
    context = {
        'circle': circle,
        'number_of_member': members_count,
        'circle_members': circles_utils.CircleUtils.get_circle_members(circle),
        'loans': {
            'loans_disbursed': loan_utils.LoanUtils.get_total_loans_disbursed_by_circle(circle),
            'repaid': loan_utils.LoanUtils.get_total_repaid_loans_by_circle(circle),
            'bad_loans': loan_utils.LoanUtils.get_bad_loans_by_circle(circle)
        },
        'shares': {
            'total_shares':  shares_utils.SharesUtils.get_circles_total_shares(circle),
            'available_shares': shares_utils.SharesUtils.get_circles_available_shares(circle),
            'locked_shares': shares_utils.SharesUtils.get_circle_locked_shares(circle)
        }
    }
    return render(request, 'app_admin/circle_details.html', context)


def get_member_shares_trx(request, circle_member_id):
    context = shares_utils.SharesUtils.get_shares_trx_by_circle_member(circle_member_id)
    return render(request, 'app_admin/member_shares_trx.html', context)


@login_required(login_url='app_admin:login_page')
def search_revenue_stream_by_date(request):
    start_date_str = request.POST.get('start_date_val').strip()
    end_date_str = request.POST.get('end_date_val').strip()
    start_date = None
    if start_date_str is not None:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        except Exception as exp:
            start_date = None

    end_date = None
    if end_date_str is not None:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
        except Exception as exp:
            end_date = None
    context = {
        'revenue_streams': revenue_streams_utils.RevenueStreamsUtils.get_revenue_by_date(start_date, end_date)
    }
    return render(request, 'app_admin/revenue_streams_list.html', context)


@login_required(login_url='app_admin:login_page')
def get_revenue_streams(request):
    context = {
        'revenue_streams': revenue_streams_utils.RevenueStreamsUtils.get_revenue_by_date()
    }
    return render(request, 'app_admin/revenue_streams_list.html', context)


@login_required(login_url='app_admin:login_page')
def commit_c2b_mpesa_transaction(request):
    if request.method != 'POST':
        # context = {
        #     'circles': circles_utils.CircleUtils.get_all_circles(),
        #     'members': members_utils.MemberUtils.get_all_members()
        # }
        return render(request, 'app_admin/c2b_transaction.html')

    else:
        print(request.POST)
        sms_instance = sms_utils.Sms()
        admins = ['+254712388212', '+254795891656', '+254714642293']
        admin_phone_number = sms_instance.format_phone_number(request.POST.get('admin_phone_number'))
        if admin_phone_number not in admins:
            return_data = {'status':0, 'message':'Unauthorized access.'}
            print(return_data)
            return HttpResponse(json.dumps(return_data))

        pin = request.POST.get('pin')
        user = authenticate(username=admin_phone_number, password=pin)
        if user is not None:
            code = request.POST.get('transaction_code')
            amount = int(request.POST.get('amount'))
            recipient_phone_number = sms_instance.format_phone_number(request.POST.get('recipient_phone_number'))
            try:
                member = Member.objects.get(phone_number=recipient_phone_number)
            except Member.DoesNotExist:
                return_data = {'status': 0, 'message':'Member with phone number does not exist'}
                return HttpResponse(json.dumps(return_data))

            transacted_by = request.POST.get('sender_phone_number')
            if len(transacted_by):
                transacted_by = sms_instance.format_phone_number(transacted_by)
            else:
                transacted_by = recipient_phone_number
            created_objects = []
            try:
                response_data = "Mpesa transaction was manually committed by {} {} {}".format(user.first_name,
                                                                                             user.last_name,
                                                                                             admin_phone_number)
                admin_mpesa_transaction = AdminMpesaTransaction_logs.objects.create(TransactioID=code,
                                                                                    TransactionType='C2B',
                                                                                    Response=response_data, is_committed=False)
                created_objects.append(admin_mpesa_transaction)
                wallet_instance = wallet_utils.Wallet()
                wallet = member.wallet
                wallet_balance = wallet_instance.calculate_wallet_balance(wallet) + amount
                transaction_desc = "{} confirmed.You have received {} {} from {} via mpesa. " \
                "New wallet balance is {} {}".format(code, member.currency, amount,
                                                     transacted_by, member.currency, wallet_balance)
                mpesa_transactions = Transactions.objects.create(wallet=wallet, transaction_type="CREDIT",
                                                                 transaction_desc=transaction_desc,
                                                                 transacted_by=transacted_by,
                                                                 transaction_amount=amount,
                                                                 transaction_code=code,
                                                                 source="MPESA C2B")
                created_objects.append(mpesa_transactions)
                admin_mpesa_transaction.is_committed = True
                admin_mpesa_transaction.is_manually_committed = True
                admin_mpesa_transaction.save()
                message = "{} {} {} has successfully committed {} mpesa transaction {} of {} {}.".format(user.first_name,
                                                                                                      user.last_name,
                                                                                                      admin_phone_number,
                                                                                                      recipient_phone_number,
                                                                                                      code,
                                                                                                      member.currency,
                                                                                                      amount)
                try:
                    sms_instance.sendsms("0755564433", message)
                except Exception as e:
                    print(str(e))
                    return_data = {'status': 0, 'message':'Transaction unsuccessful.Unable to notify admins.'}
                    return HttpResponse(json.dumps(return_data))
            except Exception as e:
                print(str(e))
                general_utils.General().delete_created_objects(created_objects)
                return_data = {'status': 0, 'message':'Unable to commit transaction'}
                return HttpResponse(json.dumps(return_data))
            serializer = WalletTransactionsSerializer(mpesa_transactions)
            instance = fcm_utils.Fcm()
            registration_id = member.device_token
            fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                        "transaction": serializer.data}
            instance.data_push("single", registration_id, fcm_data)
            return_data = {'status': 0, 'message': 'Transaction successfully committed.'}
            return HttpResponse(json.dumps(return_data))
        else:
            return_data = {'status': 0, 'message':'Invalid admin credentials'}
            return HttpResponse(json.dumps(return_data))


@login_required(login_url='app_admin:login_page')
def view_circle_invites_referrals(request):
    referrals = ReferralFee.objects.all().order_by('-id')
    return render(request, 'app_admin/referrals_list.html', {'referrals':referrals})

@login_required(login_url='app_admin:login_page')
def get_airtime_logs(request):
    airtime_logs = AirtimePurchaseLog.objects.all().order_by('-id')
    logs = []
    for obj in airtime_logs:
        if obj.amount == 0:
            amount = transactions_utils.TransactionUtils().get_airtime_amount(obj.originator_conversation_id)
        else:
            amount = obj.amount
        logs.append({
            "member": obj.member,
            "recipient": obj.recipient,
            "amount": amount,
            "is_purchased": obj.is_purchased,
            "time_of_transaction": obj.time_of_transaction,
            "extra_info": obj.extra_info
        })
    return render(request, 'app_admin/airtime_logs.html', {'airtime_logs':logs})



import json

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from . import members_utils, circles_utils, loan_utils, revenue_streams_utils, circle_withdrawal_utils, transactions_utils
from . import chat_utils


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
    user = User.objects.get(username=username)

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


def home_page(request):
    context = {
        'member': {
            'total_members': members_utils.MemberUtils.get_num_of_members(),
            'registered_today': members_utils.MemberUtils.get_num_of_members_registered__by_day()
        },
        'circle': {
            'num_of_circles': cirles_utils.CircleUtils.get_num_of_circles(),
            'num_of_active_circles': cirles_utils.CircleUtils.get_num_of_active_circles(),
            'num_of_circles_created_today': cirles_utils.CircleUtils.get_num_of_circles_registered__by_day()
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
        'shares_withdrawal': {
            'total_withdrawals_today': sum([x[0] for x in circle_withdrawal_utils.CircleWithdrawalUtils.get_shares_withdrawal_by_date()
                                .values_list('num_of_shares')]),
            'num_of_withdrawals': circle_withdrawal_utils.CircleWithdrawalUtils.get_shares_withdrawal_by_date().count(),
            'revenue': sum([x[0] for x in revenue_streams_utils.RevenueStreamsUtils.get_revenue_streams_by_date()
                           .filter(stream_type__icontains='SHARES')
                           .values_list('stream_amount')])
        }
    }
    return render(request, 'app_admin/base_dashboard.html', context)


def members_page(request):
    context = {}
    return render(request, 'app_admin/members.html', context)


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


def view_member_details(request, member_id):
    request.session['member_id'] = member_id
    member = members_utils.MemberUtils.get_member_from_id(member_id)
    context = {
        'member': member,
        'next_of_kin': members_utils.MemberUtils.get_next_of_kin(member),
        'circles': cirles_utils.CircleUtils.get_circles_by_member(member),
        'transactions': transactions_utils.TransactionUtils.get_wallet_transaction_by_member(member)[:100]
    }
    return render(request, 'app_admin/member_details.html', context)


def wallet_transactions(request):
    context = {}
    return render(request, 'app_admin/wallet_transactions_list.html', context)


def search_for_transaction(request):
    transactions = []
    search_val = request.POST.get('search_val')
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


def view_transaction_details(request, transaction_id):
    request.session['transaction_id'] = transaction_id
    trx = transactions_utils.TransactionUtils.get_transaction_by_id(transaction_id)
    context = {
        'transaction': trx,
        'current_balance': transactions_utils.TransactionUtils.get_wallet_balance_wallet_id(trx.wallet.id)
    }
    return render(request, 'app_admin/wallet_transaction.html', context)


def loan_applications(request):
    context = {}
    template = 'app_admin/loan_applications_list.html'
    return render(request, template, context)


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


def chats_list(request):
    context = {
        'chats': chat_utils.ChatUtils.get_pending_chats()
    }
    return render(request, 'app_admin/chats.html', context)


def reply_to_chat(request):
    chat_id = request.POST.get('chat_id')
    body = request.POST.get('body')
    reply_chat = chat_utils.ChatUtils.reply_to_chat(chat_id, body)
    response = {
        'status': 1 if reply_chat else 0,
        'message': 'Sent' if reply_chat else 'Failed',
    }
    return HttpResponse(json.dumps(response))


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

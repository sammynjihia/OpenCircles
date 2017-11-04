import json

from django.shortcuts import render
from django.http import HttpResponse
from . import members_utils, cirles_utils, loan_utils, revenue_streams_utils, circle_withdrawal_utils, transactions_utils


# Create your views here.


def create_admin(request):
    pass


def lock_admin_acc(request):
    pass


def login_page(request):
    return render(request, 'app_admin/login_page.html', {})

def login_admin(request):
    pass


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
        'circles': cirles_utils.CircleUtils.get_circles_by_member(member),
        'transactions': transactions_utils.TransactionUtils.get_wallet_transaction_by_member(member)
    }
    return render(request, 'app_admin/member_details.html', context)


def wallet_transactions(request):
    context = {}
    return render(request, 'app_admin/wallet_transaction.html', context)


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
    return render(request, 'app_admin/transaction.html', context)









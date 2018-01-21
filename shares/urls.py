from django.conf.urls import url
from shares import views

urlpatterns = [
    url(r'^$', views.api_root, name='api-root'),
    url(r'^purchase_shares/$', views.PurchaseShares.as_view(), name='purchase-shares'),
    url(r'^view_shares/$', views.MemberShares.as_view(), name='view-shares'),
    url(r'^shares_transaction/$', views.MemberSharesTransactions.as_view(), name='shares-transaction'),
    url(r'^shares_withdrawal_tariff/$', views.get_shares_withdrawal_tariff, name='shares-withdrawal-tariff'),
    url(r'^withdraw_shares/$', views.SharesWithdrawal.as_view(), name='shares_withdrawal')
]

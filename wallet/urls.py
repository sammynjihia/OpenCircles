from django.conf.urls import url
from . import views

urlpatterns = [
   url(r'^$',views.api_root, name="api_root"),
   url(r'^wallet_to_wallet/$', views.WallettoWalletTranfer.as_view(), name="wallet-tranfer"),
   url(r'^wallet_transactions/$', views.TransactionsDetails.as_view(), name="wallet-transactions"),
   url(r'^get_wallet_transaction/$', views.WalletTransactionDetails.as_view(), name="wallet-transaction"),
   url(r'^wallet_transactions/$', views.TransactionsDetails.as_view(), name="wallet-transactions"),
   url(r'^mpesa_lipa_online_initiate/$', views.MpesaToWallet.as_view(), name="mpesa_lipa_online_initiate"),
   url(r'^mpesaCallbackURL/$', views.MpesaCallbackURL.as_view(), name="mpesaCallbackURL"),
   url(r'^mpesaB2CResultURL/$', views.MpesaB2CResultURL.as_view(), name="mpesaB2CResultURL"),
   url('^mpesaB2CQueueTimeoutURL/$', views.MpesaB2CQueueTimeoutURL.as_view(), name="mpesaB2CQueueTimeoutURL"),
   url(r'^mpesa_B2C_checkout_initiate/$', views.WalletToMpesa.as_view(), name="mpesa_B2C_checkout_initiate"),
   url(r'^mpesaC2BConfirmationURL/$', views.MpesaC2BConfirmationURL.as_view(), name="mpesaC2BConfirmationURL"),
   url(r'^mpesaC2BValidationURL/$', views.MpesaC2BValidationURL.as_view(), name="mpesaC2BValidationURL"),
   url(r'^get_brain_tree_token', views.brain_tree_client_token, name="brain-tree-token"),
   url(r'^wallet_to_paybill/$', views.WalletToPayBill.as_view(), name="wallet_to_paybill"),
   url(r'^mpesaB2BResultURL/$', views.MpesaB2BResultURL.as_view(), name="mpesaB2BResultURL"),
   url(r'^wallet_to_bank/$', views.WalletToBankPayBill.as_view(), name="wallet_to_bank"),
   url(r'^buy_airtime/$', views.PurchaseAirtime.as_view(), name="purchase_airtime"),
]

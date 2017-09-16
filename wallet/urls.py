from django.conf.urls import url
from . import views

urlpatterns = [
   url(r'^$',views.api_root,name="api_root"),
   url(r'^wallet_to_wallet/$',views.WallettoWalletTranfer.as_view(),name="wallet-tranfer"),
   url(r'^wallet_transactions/$',views.TransactionDetails.as_view(),name="wallet-transactions"),
   url(r'^mpesa_lipa_online_initiate/$', views.MpesaToWallet.as_view(), name="mpesa_lipa_online_initiate"),
   url(r'^mpesaCallbackURL/$', views.MpesaCallbackURL.as_view(), name="mpesaCallbackURL")
]

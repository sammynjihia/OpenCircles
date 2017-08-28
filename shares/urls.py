from django.conf.urls import url
from shares import views

urlpatterns = [
    url(r'^$',views.api_root,name='api-root'),
    url(r'^purchase_shares/$',views.PurchaseShares.as_view(),name='purchase-shares'),
    url(r'^view_shares/$',views.MemberShares.as_view(),name='view-shares'),
]

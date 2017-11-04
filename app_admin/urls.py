from django.conf.urls import url
from . import views


app_name = 'app_admin'
urlpatterns = [
    url(r'^login_page$', views.login_page, name='login_page'),
    url(r'^home$', views.home_page, name='home'),
    url(r'^members$', views.members_page, name='members'),
    url(r'^search_for_member$', views.search_for_member, name='search_for_member'),
    url(r'^view_member_details/(?P<member_id>[0-9]+)/$', views.view_member_details, name='view_member_details'),
    url(r'^wallet_transactions$', views.wallet_transactions, name='wallet_transactions'),
    url(r'^search_for_transaction$', views.search_for_transaction, name='search_for_transaction'),
    url(r'^view_transaction_details/(?P<transaction_id>[0-9]+)/$', views.view_transaction_details,
        name='view_transaction_details')
]














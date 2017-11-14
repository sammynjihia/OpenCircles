from django.conf.urls import url
from . import views


app_name = 'app_admin'
urlpatterns = [
    url(r'^login_page$', views.login_page, name='login_page'),
    url(r'^login_admin$', views.login_admin, name='login_admin'),
    url(r'^logout_admin$', views.logout_admin, name='logout_admin'),
    url(r'^home$', views.home_page, name='home'),
    url(r'^members$', views.members_page, name='members'),
    url(r'^search_for_member$', views.search_for_member, name='search_for_member'),
    url(r'^view_member_details/(?P<member_id>[0-9]+)/$', views.view_member_details, name='view_member_details'),
    url(r'^wallet_transactions$', views.wallet_transactions, name='wallet_transactions'),
    url(r'^search_for_transaction$', views.search_for_transaction, name='search_for_transaction'),
    url(r'^view_transaction_details/(?P<transaction_id>[0-9]+)/$', views.view_transaction_details,
        name='view_transaction_details'),
    url(r'^mpesa_transactions$', views.mpesa_transactions, name = 'mpesa_transactions'),
    url(r'^search_for_mpesa_transaction$', views.search_for_mpesa_transaction, name='search_for_mpesa_transaction'),
    url(r'^view_mpesa_transaction/(?P<transaction_code>[A-Za-z0-9]+)/$', views.view_mpesa_transaction, name='view_mpesa_transaction'),
    url(r'^commit_mpesa_transaction$', views.commit_mpesa_transaction, name='commit_mpesa_transaction'),
    url(r'^transactions_days_analytics$', views.transactions_days_analytics, name='transactions_days_analytics'),
    url(r'^loan_applications$', views.loan_applications, name='loan_applications'),
    url(r'^search_for_loan_applications$', views.search_for_loan_applications, name='search_for_loan_applications'),
    url(r'^view_loan_application_details/(?P<loan_code>[A-Za-z0-9]+)/$', views.view_loan_application_details,
        name='view_loan_application_details'),
    url(r'^chats$', views.chats_list, name='chats'),
    url(r'^reply_to_chat', views.reply_to_chat, name='reply_to_chat'),
    url(r'^search_for_chats$', views.search_for_chats, name='search_for_chats'),
    url(r'^circles_list$', views.circles_list, name='circles_list'),
    url(r'^view_circle_details/(?P<circle_id>[A-Za-z0-9]+)/$', views.view_circle_details,
        name='view_circle_details'),
    url(r'^get_revenue_streams$', views.get_revenue_streams,  name='get_revenue_streams'),
    url(r'^search_revenue_stream_by_date$',  views.search_revenue_stream_by_date, name='search_revenue_stream_by_date'),


]














from django.conf.urls import url,include
from . import views


urlpatterns = [
    url(r'^$',views.api_root,name='api-root'),
    url(r'^register_member/$',views.MemberRegistration.as_view(),name='member-registration'),
    url(r'^confirm_phone_number/$',views.PhoneNumberConfirmation.as_view(),name='confirm-number'),
    url(r'^change_password/$',views.ChangePassword.as_view(),name='change-password'),
    url(r'^login/$',views.LoginIn.as_view(),name = 'login'),
    url(r'^logout/$',views.logout,name='logout')
]

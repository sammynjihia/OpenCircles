from django.conf.urls import url,include
from . import views


urlpatterns = [
    url(r'^register_member/$',views.MemberRegistration.as_view(),name='member-registration'),
    url(r'^confirm_phone_number/$',views.PhoneNumberConfirmation.as_view(),name='confirm-number'),
    url(r'^change_password/$',views.ChangePassword.as_view(),name='change-password'),
    url(r'^login_member/$',views.LoginIn.as_view(),name = 'login'),
    url(r'^logout/$',views.logout,name='logout'),
    url(r'^update_app_token/$',views.UpdateDeviceToken.as_view(),name='update-app-token'),
    url(r'^reset_pin/$',views.ResetPin.as_view(),name='reset-pin'),
    url(r'^send_verification_code/$',views.send_short_code,name='send-short-code')
]

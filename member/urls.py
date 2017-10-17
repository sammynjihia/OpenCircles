from django.conf.urls import url,include
from rest_framework.routers import DefaultRouter
from . import views

# router = DefaultRouter()
# router.register(r'members_list',views.MemberViewSet)

urlpatterns = [
    # url(r'^',include(router.urls)),
    # url(r'^$',views.api_root),
    url(r'^member_details/$',views.MemberDetail.as_view(),name='member-detail'),
    url(r'^register_beneficiary/$',views.BeneficiaryRegistration.as_view(),name='register-beneficiary'),
    url(r'^member_beneficiaries/$',views.MemberBeneficiary.as_view(),name='member-beneficiary'),
    url(r'^add_new_contact/$',views.save_new_contact,name='add-new-contact')
]

from django.conf.urls import url
from loan import views

urlpatterns = [
    url(r'^$',views.api_root,name='api-root'),
    url(r'^loan_application/$',views.LoanApplication.as_view(),name='loan_application'),
]

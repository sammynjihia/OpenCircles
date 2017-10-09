from django.conf.urls import url
from loan import views

urlpatterns = [
    url(r'^$',views.api_root,name='api-root'),
    url(r'^loan_application/$',views.LoanApplication.as_view(),name='loan_application'),
    url(r'^my_loans/$', views.Loans.as_view(), name='my_loans'),
    url(r'^repay_loan/$',views.LoanRepayment.as_view(),name='repay_loan'),
    url(r'^loan_guarantors/$',views.LoanGuarantors.as_view(),name='loan_guarantors'),
    url(r'^add_loan_guarantor/$',views.NewLoanGuarantor.as_view(),name='add-loan-guarantor'),
    url(r'^remove_loan_guarantor/$',views.remove_loan_guarantor,name='remove_loan_guarantor'),
    url(r'^get_loan_amortization/$',views.AmortizationSchedule.as_view(),name='amortization_schedule'),
    url(r'^get_loan_repayment/$',views.LoanRepaymentDetails.as_view(),name='loan_repayment_details'),
    url(r'^process_guarantee_loan_request/$',views.LoanGuarantorResponse.as_view()),
    url(r'^unprocessed_guarantee_loan_requests/$',views.UnprocessedLoanGuarantorRequest.as_view()),
]

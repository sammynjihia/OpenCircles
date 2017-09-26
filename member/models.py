from django.db import models
from django.contrib.auth.models import User
import urllib, os
from urlparse import urlparse
from app_utility import sms_utils

# Create your models here.

GENDER_CHOICES = (('Male', 'Male'), ('Female', 'Female'))
upload_path ='MEDIA/MEMBER_PASSPORT_PICS'

class PendingRegistration(models.Model):
    national_id = models.CharField(max_length=20, blank=False, unique=True)
    first_name = models.CharField(max_length=20, blank=False)
    last_name = models.CharField(max_length=20, blank=False)
    phone_number = models.CharField(max_length=20, blank=False, unique=True)
    email_address = models.EmailField(max_length=100, blank=False, unique=True)
    registered_device = models.TextField(max_length=1000, blank=True)
    nationality = models.CharField(max_length=20, blank=True)
    time_created = models.DateTimeField(auto_now=True)
    has_agreed_to_terms = models.BooleanField(default=False)
    universal_transaction_pin = models.CharField(max_length=1000, blank=True)
    national_id_confirmed = models.BooleanField(default=False)
    phone_number_confirmed = models.BooleanField(default=False)
    email_address_confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = 'PendingRegistration'


class Member(models.Model):
    """
        A class that stores the Investor
    """

    user = models.OneToOneField(User,on_delete=models.CASCADE)
    national_id = models.CharField(max_length=20, blank=False, unique=True)
    phone_number = models.CharField(max_length=20, blank=False, unique=True)
    other_name = models.CharField(max_length=20,default="")
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True)
    iprs_image_url = models.URLField(null=True, blank=True)
    iprs_image = models.ImageField(upload_to=upload_path, null=True, blank=True)
    image = models.ImageField(upload_to="MEMBER_PROFILE_PICS",null=True,blank=True)
    registered_device = models.TextField(max_length=1000, blank=True)
    currency = models.CharField(max_length=10,default="KES")
    occupation = models.CharField(max_length=100, blank=True)
    time_registered = models.DateTimeField(auto_now_add=True)
    is_validated = models.BooleanField(default = False)
    device_token = models.CharField(max_length=300,default='')

    class Meta:
        db_table = 'Member'

    def save(self, *args, **kwargs):
        if self.iprs_image_url:
            file_save_dir = upload_path
            file_path = 'MEMBER_PASSPORT_PICS'
            filename = urlparse(self.iprs_image_url).path.split('/')[-1]
            urllib.urlretrieve(self.iprs_image_url, os.path.join(file_save_dir, filename))
            self.iprs_image = os.path.join(file_path, filename)
            self.iprs_image_url = ''
        return super(Member, self).save()

class Beneficiary(models.Model):
    """
        A class that stores a beneficiary of an member
    """
    RELATIONSHIP_CHOICES = (
        ('CHILD', 'Child'),
        ('SPOUSE', 'Spouse'),
        ('PARENT', 'Parent'),
        ('OTHER', 'Other')
    )

    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE,related_name='owner')
    first_name = models.CharField(max_length=20, blank=False)
    last_name = models.CharField(max_length=20, blank=False)
    gender = models.CharField(max_length=7, choices=GENDER_CHOICES)
    relationship = models.CharField(max_length=10, choices=RELATIONSHIP_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True)
    benefit = models.FloatField(default=0.00)
    passport_image = models.FileField(storage='MEDIA/BENEFICIARY_PASSPORT_IMAGE', null=True, blank=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Beneficiary'

    def save(self,*args,**kwargs):
        instance = sms_utils.Sms()
        self.phone_number = instance.format_phone_number(self.phone_number)
        self.benefit = self.benefit/100
        return super(Beneficiary,self).save()



class MemberBankAccount(models.Model):
    """
        A class for storing an member account
    """
    member = models.OneToOneField(Member, null=False, blank=False)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch_name = models.CharField(max_length=100, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=100, blank=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MemberBankAccount'


class MemberBankCard(models.Model):
    """
        A class for storing an member credit cards
    """
    member = models.OneToOneField(Member, null=False, blank=False, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=20, blank=False, unique=True)
    expires_on = models.CharField(max_length=5, blank=False)
    card_verification_value = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MemberBankCard'


class MemberActiveSession(models.Model):
    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    session_info = models.TextField(max_length=1000, blank=True)
    session_start_time = models.DateTimeField(auto_now=True)
    session_end_time = models.DateTimeField(null=True)

    class Meta:
        db_table = 'MemberActiveSession'

class Contacts(models.Model):
    member = models.ForeignKey(Member,on_delete = models.CASCADE)
    name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    is_member = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=False)

    class Meta():
        db_table = 'Contacts'

    def save(self,*args,**kwargs):
        try:
            Member.objects.get(phone_number=self.phone_number)
            self.is_member = True
        except Member.DoesNotExist:
            self.is_member = False
        return super(Contacts,self).save()

from django.db import models

# Create your models here.

GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'))


class Member(models.Model):
    """
        A class that stores the Investor
    """
    national_id = models.CharField(max_length=20, blank=False, unique=True)
    phone_number = models.CharField(max_length=20, blank=False, unique=True)
    email_address = models.EmailField(max_length=100, blank=False, unique=True)
    first_name = models.CharField(max_length=20, blank=False)
    last_name = models.CharField(max_length=20, blank=False)
    other_name = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True)
    profile_picture = models.FileField(storage='PROFILE_PICTURES')
    registered_device = models.TextField(max_length=10000, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    other_info = models.TextField(max_length=10000, blank=True)
    is_active = models.BooleanField(default=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Member'


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

    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=20, blank=False)
    last_name = models.CharField(max_length=20, blank=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    relationship = models.CharField(max_length=10, choices=RELATIONSHIP_CHOICES)
    date_of_birth = models.DateField(null=True)
    other_info = models.TextField(max_length=10000, blank=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Beneficiary'


class MemberBankAccount(models.Model):
    """
        A class for storing an member account
    """
    member = models.OneToOneField(Member, null=False, blank=False)
    account_id = models.CharField(max_length=100, blank=False, unique=True)
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
    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=20, blank=False, unique=True)
    expires_on = models.CharField(max_length=5, blank=False)
    cvv = models.CharField(max_length=10, blank=True)
    other_info = models.TextField(max_length=10000, blank=True)
    time_created = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'MemberBankCard'


class MemberActiveSession(models.Model):
    member = models.ForeignKey(Member, null=False, blank=False, on_delete=models.CASCADE)
    session_info = models.TextField(max_length=10000, blank=True)
    session_start_time = models.DateTimeField(auto_now=True)
    session_end_time = models.DateTimeField(null=True)

    class Meta:
        db_table = 'MemberActiveSession'







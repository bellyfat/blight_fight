from django import forms
from django.conf import settings
#from allauth.accounts.forms import SignupForm
#from allauth.account.forms import SignupForm as allauthSignupForm
#from allauth import accounts
from applicants.models import Organization, ApplicantProfile
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, ButtonHolder, Div, Button, MultiField, Field, HTML
from crispy_forms.bootstrap import FormActions
from passwords.fields import PasswordField
from localflavor.us.forms import USPhoneNumberField, USZipCodeField, USPSSelect, USStateField, USStateSelect

from .widgets import AddAnotherWidgetWrapper
from mailchimp3 import MailChimp
from django.utils.timezone import now
from ipware import get_client_ip


class OrganizationForm(forms.ModelForm):
    phone_number = USPhoneNumberField(required=False)
    mailing_address_state = USStateField(
        widget=USStateSelect, required=True, label='State')
    mailing_address_zip = USZipCodeField(required=True, label='Zipcode')

    class Meta:
        model = Organization
        exclude = ['user', 'date_created']

    def __init__(self, *args, **kwargs):
        super(OrganizationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'OrganizationForm'
        self.helper.form_class = 'form-horizontal'
        #self.helper.field_class = 'col-lg-4'
        #self.helper.label_class = 'col-lg-2'
        self.helper.form_tag = True

        self.helper.layout = Layout(
            Fieldset(
                'Add Third Party Buyer',
                HTML("""
						<p>If you are applying on behalf of an organization, family member, client or other third party who will take title, provide their name and contact information.</p>
					"""),
                Field('name'),
                Field('email'),
                Field('phone_number'),
                css_class='well'
            ),
            Fieldset(
                'Type and Relationship',
                Field('entity_type'),
                Field('relationship_to_user'),
                css_class='well'
            ),
            Fieldset(
                'Mailing Address',
                Field('mailing_address_line1'),
                Field('mailing_address_line2'),
                Field('mailing_address_line3'),
                Field('mailing_address_city'),
                Field('mailing_address_state'),
                Field('mailing_address_zip'),
                css_class='well'
            ),
            Fieldset(
                'Supporting Documents',
                HTML("""
						<p>Organizations should provide additional identifying and financial documents.</p>
					"""),
                Field('sos_business_entity_report'),
                #Field('irs_determination_letter'),
                #Field('most_recent_financial_statement'),
                #HTML('<div class="form-group"><div class="control-label col-lg-4">Attach a file</div><div id="file-uploader" class="form-control-static col-lg-6">Drop your file here to upload</div>'),
                css_class='well'
            ),
            FormActions(
                #Button('cancel', 'Cancel'),
                Submit('save', 'Save')
            )
        )
        self.helper.form_method = 'post'
        self.helper.form_action = ''

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name')
    phone_number = USPhoneNumberField()
    mailing_address_line1 = forms.CharField(
        max_length='100', required=True, label='Mailing Address Line 1', help_text='Pursuant to IC Code 32-21-2-3 we are no longer allowed to use a PO Box for tax mailing address purposes.')
    mailing_address_line2 = forms.CharField(
        max_length='100', required=False, label='Mailing Address Line 2')
    mailing_address_line3 = forms.CharField(
        max_length='100', required=False, label='Mailing Address Line 3')
    mailing_address_city = forms.CharField(
        max_length='100', required=True, label='Mailing Address City')
    mailing_address_state = USStateField(
        widget=USStateSelect, required=True, label='Mailing Address State')
    mailing_address_zip = USZipCodeField(required=True, label='Zipcode')
    opt_in_newsletter = forms.BooleanField(
        required=False,
        #default=True,
        widget=forms.widgets.CheckboxInput(attrs={'checked' : 'checked'}),
        label='Subscribe to the Renew Indianapolis email newsletter',
        help_text='Stay up to date with our email newsletter'
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__exact=email).count() > 0:
            raise forms.ValidationError(
                "Looks like an account with this email address already exists, did you forget your password?")
        return email
    def raise_duplicate_email_error(self):
        # here I tried to override the method, but it is not called
        raise forms.ValidationError(
            _("An account already exists with this e-mail address."
              " Please sign in to that account."))



    def subscribe_to_newsletter(self, request, user, opt_in):
        client = MailChimp(mc_api=settings.MAILCHIMP_API_KEY, mc_user=settings.MAILCHIMP_USERNAME)
        user_ip, is_routable = get_client_ip(request)
        if opt_in:
            status = 'subscribed'
        else:
            status = 'unsubscribed'
        return client.lists.members.create(settings.MAILCHIMP_NEWSLETTER_ID, {
            'email_address': user.email,
            'status': status,
            'merge_fields': {
                'FNAME': user.first_name,
                'LNAME': user.last_name,
            },
            'ip_signup': user_ip,
            })


    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.username = user.email # username is 30 characters, email is 254. Switching to 254 or 150 or something in Django 1.9
        user.save()
        profile = ApplicantProfile()
        profile.phone_number = self.cleaned_data['phone_number']
        profile.mailing_address_line1 = self.cleaned_data[
            'mailing_address_line1']
        profile.mailing_address_line2 = self.cleaned_data[
            'mailing_address_line2']
        profile.mailing_address_line3 = self.cleaned_data[
            'mailing_address_line3']
        profile.mailing_address_city = self.cleaned_data[
            'mailing_address_city']
        profile.mailing_address_state = self.cleaned_data[
            'mailing_address_state']
        profile.mailing_address_zip = self.cleaned_data['mailing_address_zip']
        profile.user = user
        profile.save()
        # This is where we would push signup to MailChimp
        try:
            attempt_subscribe = self.subscribe_to_newsletter(request, user, self.cleaned_data['opt_in_newsletter'])
        except:
            pass

class ApplicantProfileForm(forms.ModelForm):
        # organization = forms.ModelChoiceField(
    #     queryset=Organization.objects.all().order_by('name'),
    #     widget=AddAnotherWidgetWrapper(
    #         forms.Select(),
    #         Organization,
    #     ),
        # 	required=False
    # )

    class Meta:
        model = ApplicantProfile
        exclude = ['user', 'external_system_id', 'staff_notes']

    def __init__(self, *args, **kwargs):
        super(ApplicantProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'ApplicantProfileForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.field_class = 'col-lg-4'
        self.helper.label_class = 'col-lg-2'
        self.helper.render_unmentioned_fields = False
        self.helper.layout = Layout(
            Fieldset(
                'Add Details',
                Field('phone_number'),
                css_class='well'
            ),
            Fieldset(
                'Mailing Address',
                Field('mailing_address_line1'),
                Field('mailing_address_line2'),
                Field('mailing_address_line3'),
                Field('mailing_address_city'),
                Field('mailing_address_state'),
                Field('mailing_address_zip'),
                css_class='well'
            ),
            FormActions(
                #Button('cancel', 'Cancel'),
                Submit('save', 'Save')
            )
        )
        self.helper.form_method = 'post'
        self.helper.form_action = ''

# class CustomSignupForm(allauthSignupForm ):
#     def raise_duplicate_email_error(self):
#         # here I tried to override the method, but it is not called
#         raise forms.ValidationError(
#             _("An account already exists with this e-mail address."
#               " Please sign in to that account."))

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.gis.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import python_2_unicode_compatible
from os.path import basename
import pyclamd
from django.core.mail import send_mail
from PIL import Image, ExifTags


@python_2_unicode_compatible
class Entity(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(get_user_model())

    name = models.CharField(max_length=100, blank=False)
    created_boolean = models.BooleanField(default=False)
    date_of_creation = models.DateField(blank=True, null=True)
    location_of_creation = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = 'Entities'

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Person(models.Model):
    entity = models.ForeignKey(Entity)
    name = models.CharField(max_length=100, blank=False)
    title = models.CharField(max_length=100, blank=True, help_text='Job Title')
    email = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    nature_extent_of_interest = models.CharField(max_length=512, blank=True)

    class Meta:
        verbose_name_plural = 'People'

    def __str__(self):
        if len(self.title) > 20:
            title = '{}...'.format(self.title[:17])
        else:
            title = self.title
        return '{} - {}'.format(self.name, title)


@python_2_unicode_compatible
class Note(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    text = models.CharField(
        max_length=5000,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(get_user_model())
    public = models.BooleanField(help_text='Is this note public?')

    def __str__(self):
        if len(self.text) > 17:
            elipse = '...'
        else:
            elipse = ''
        return '{}{} @ {}'.format(self.text[:20], elipse, self.modified.strftime('%c'))



@python_2_unicode_compatible
class Document(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    user = models.ForeignKey(get_user_model())

    file = models.FileField(
        upload_to="documents/%Y/%m/%d", max_length=512)

    file_purpose = models.CharField(
        verbose_name='Briefly describe this file',
        blank=True,
        max_length=255
    )

    publish = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)
        try:
            cd = pyclamd.ClamdUnixSocket()
            # test if server is reachable
            cd.ping()
        except pyclamd.ConnectionError:
            # if failed, test for network socket
            cd = pyclamd.ClamdNetworkSocket()
        try:
            cd.ping()
        except pyclamd.ConnectionError:
            raise ValueError('could not connect to clamd server either by unix or network socket')

        scan_results = cd.scan_file(self.file.path)
        if scan_results is not None:
            print 'Virus found:', scan_results
            send_mail('Django Virus Found', 'Virus found in file uploaded', 'info@renewindianapolis.org',
        ['chris.hartley@renewindianapolis.org'], fail_silently=False)
            return True
        else:
#            super(photo, self).save(*args, **kwargs) # have to save object first to get the file in the right place
            try:
                im = Image.open(self.file.path)
                # image rotation code from http://stackoverflow.com/a/11543365/2731298
                e = None
                if hasattr(im, '_getexif'): # only present in JPEGs
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation]=='Orientation':
                            break
                    e = im._getexif()       # returns None if no EXIF data
                if e is not None:
                    exif=dict(e.items())
                    orientation = exif.get(orientation, None)
                    if orientation == 3:   im = im.transpose(Image.ROTATE_180)
                    elif orientation == 6: im = im.transpose(Image.ROTATE_270)
                    elif orientation == 8: im = im.transpose(Image.ROTATE_90)
    #            im.thumbnail((1024,1024))
                im.save(self.image.path)
            except:
                return False

    def __str__(self):
        return '{} - {}'.format(basename(self.file.name), self.file_purpose[:20] )

class Photo(Document):
    pass

@python_2_unicode_compatible
class Property(models.Model):

    AVAILABLE_STATUS = 'Available'
    SALE_PENDING_STATUS = 'Sale Pending'
    ON_HOLD_STATUS = 'On Hold'
    SOLD_STATUS = 'Sold'

    STATUS_CHOICES = (
        (AVAILABLE_STATUS, AVAILABLE_STATUS),
        (SALE_PENDING_STATUS, SALE_PENDING_STATUS),
        (ON_HOLD_STATUS, ON_HOLD_STATUS),
        (SOLD_STATUS, SOLD_STATUS),
    )


    geometry = models.MultiPolygonField(srid=4326)
    street_address = models.CharField(max_length=512, blank=False, null=False)
    property_name = models.CharField(max_length=512, blank=False, null=False)
    status = models.CharField(choices=STATUS_CHOICES, blank=True, max_length=100)
    status_date = models.DateField(blank=True)
    parcel = models.CharField(
        max_length=7,
        unique=True,
        help_text="""
            The 7 digit local parcel number for a property, ex 1052714
        """,
        verbose_name='parcel number')
    published = models.BooleanField(default=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The price of the property",
        null=True,
        blank=True,
    )

    parcel_size = models.IntegerField(null=True)
    zoning = models.CharField(blank=True, max_length=12)
    environmental_information = models.CharField(max_length=10240, blank=True)
    has_improvement = models.NullBooleanField()
    building_size = models.IntegerField(null=True, blank=True)
    location_notes = models.CharField(max_length=5120, blank=True)
    property_notes = models.CharField(max_length=5120, blank=True)

    documents = GenericRelation(Document, related_query_name='prop')
    photos = GenericRelation(Photo)


    #def save(self):


    def __str__(self):
        return '{} - {}'.format(self.street_address, self.parcel)

    class Meta:
        verbose_name = 'Property'
        verbose_name_plural = 'Properties'

@python_2_unicode_compatible
class Application(models.Model):

    WITHDRAWN_STATUS = 1
    HOLD_STATUS = 2
    ACTIVE_STATUS = 3
    COMPLETE_STATUS = 4
    INITIAL_STATUS = 5

    STATUS_TYPES = (
        (WITHDRAWN_STATUS, 'Withdrawn'),
        (HOLD_STATUS, 'On Hold'),
        (ACTIVE_STATUS, 'Active / In Progress'),
        (COMPLETE_STATUS, 'Complete / Submitted'),
        (INITIAL_STATUS, 'Initial state'),
    )

    YES_CHOICE = True
    NO_CHOICE = False
    YESNO_TYPES = (
        (YES_CHOICE, 'Yes'),
        (NO_CHOICE, 'No')
    )

    CURRENT_STATUS = 3
    DELINQUENT_STATUS = 2
    NA_STATUS = 0

    TAX_STATUS_CHOICES = (
        (CURRENT_STATUS, 'Current'),
        (DELINQUENT_STATUS, 'Delinquent'),
        (NA_STATUS, 'N/A - No property owned')
    )


    Properties = models.ManyToManyField(Property)
    user = models.ForeignKey(get_user_model(), related_name='commind_app')

    status = models.IntegerField(
        choices=STATUS_TYPES,
        help_text="What is the internal status of this application?",
        null=False,
        default=INITIAL_STATUS,
        verbose_name='Status'
    )

    conflict_board_rc = models.NullBooleanField(
        choices=YESNO_TYPES,
        verbose_name="Do you, any family members or partner/member of your entity, or any of your entity's board members or employees work for Renew Indianapolis or serve on the Renew Indianapolis Board of Directors or Committees and thus pose a potential conflict of interest?",
        blank=True
    )

    conflict_board_rc_name = models.CharField(
        verbose_name="If yes, what is their name?",
        blank=True,
        max_length=255
    )

    conflict_city = models.NullBooleanField(
        choices=YESNO_TYPES,
        verbose_name="Do you, any family members or partner/member of your entity, or any of your entity's board members or employees serve on the Metropolitan Development Commission or are employed by the City of Indianapolis Department of Metropolitan Development and thus pose a potential conflict of interest?",
        blank=True
    )

    conflict_city_name = models.CharField(
        verbose_name="If yes, what is their name?",
        blank=True,
        max_length=255
    )

    active_citations = models.NullBooleanField(
        choices=YESNO_TYPES,
        verbose_name="Does the applicant own any property that is subject to any un-remediated citation of violation of the state and local codes and ordinances?",
        help_text="The unsafe building code and building code history of properties owned by the prospective buyer, or by individuals or entities related to the prospective buyer, will be a factor in determining eligibility.  Repeat violations, unmitigated violations, and unpaid civil penalties may cause a buyer to be ineligible",
        blank=True
    )

    tax_status_of_properties_owned = models.IntegerField(
        choices=TAX_STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name='Tax status of property currently owned in Marion County',
        help_text="If the applicants do not own any property (real estate) in Marion County chose N/A. If you chose 'Unknown' we will contact you for an explanation.",
    )

    prior_tax_foreclosure = models.NullBooleanField(
        choices=YESNO_TYPES,
        verbose_name="""
            Were the applicants the prior owner of any property in Marion County that was
            transferred to the Treasurer or to a local government as a result
            of tax foreclosure proceedings?
        """,
        blank=True
    )

    frozen = models.BooleanField(
        default=False,
        verbose_name='Freeze Application for Review',
        help_text="Frozen applications are ready for review and can not be edited by the applicant"
    )


    narrative_description = models.TextField(
        max_length=5120,
        help_text="""
            A brief narrative describing this proposed project, including the
            the work to be done, timeline, proposed end use and
            disposition after completion.

        """,
        blank=False
    )

    source_of_financing = models.TextField(
        max_length=5120,
        help_text="""
			Tell us how the applicants plan to pay for the proposed development.
            Also include any grants you plan to apply for, including the
			name of the grant and whether it is awarded, pending, or not yet
            submitted.
		""",
        blank=False
    )

    # price_at_time_of_submission = models.DecimalField(
    #     max_digits=8,
    #     decimal_places=2,
    #     help_text="The price of the property at time of submission",
    #     null=True,
    #     blank=True,
    # )


    documents = GenericRelation(Document, related_query_name='application')
    notes = GenericRelation(Note, related_query_name='application_notes')
    entity = models.ForeignKey(Entity)

    created = models.DateTimeField(auto_now_add=True)
    submitted_timestamp = models.DateTimeField(null=True, blank=True)
    modified = models.DateTimeField(auto_now=True)

    #
    # staff_notes = models.CharField(
    #     help_text="Non-public internal staff notes"
    #     blank=True,
    #     max_length=1024
    # )

    staff_recommendation = models.NullBooleanField(
        help_text="Staff recommendation to Review Comittee",
        null=True
    )

    staff_recommendation_notes = models.CharField(
        max_length=255,
        help_text="Explanation of staff recommendation to Review Comittee",
        blank=True
    )

    staff_summary = models.TextField(
        max_length=5120,
        help_text="Staff summary of application for Review Committee",
        blank=True
    )

    staff_sow_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total scope of work, as verified by staff.",
        verbose_name='Staff determined scope of work total',
        null=True,
        blank=True
    )

    staff_pof_total = models.DecimalField(max_digits=10, decimal_places=2,
        help_text="Total funds demonstrated",
        verbose_name='Staff determined PoF',
        null=True,
        blank=True
    )

    staff_pof_description = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name="Staff description of proof of funds provided"
    )

    staff_points_to_consider = models.CharField(
        verbose_name="Staff's suggested points to consider",
        max_length=255,
        blank=True
    )

    neighborhood_notification_details = models.CharField(
        blank=True,
        max_length=10240
    )

    neighborhood_notification_feedback = models.CharField(
        blank=True,
        max_length=10240
    )


    def save(self, *args, **kwargs):
        if self.status == self.COMPLETE_STATUS and self.submitted_timestamp is None:
            self.submitted_timestamp = timezone.now()
        super(Application, self).save(*args, **kwargs)

    def __str__(self):
        return '{} - {}'.format(self.created, self.user)
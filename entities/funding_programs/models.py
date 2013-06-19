# coding: utf-8

import os

from django.db import models
from django.template.defaultfilters import slugify

from entities.organizations.models import Organization

from entities.utils.models import GeographicalScope


# Create your models here.


def funding_program_logo_path(self, filename):
    return "%s/%s%s" % ("funding_programs", self.funding_program.slug, os.path.splitext(filename)[-1])


#########################
# Model: FundingProgram
#########################

class FundingProgram(models.Model):
    organization = models.ForeignKey(Organization)

    full_name = models.CharField(
        max_length=250,
    )

    short_name = models.CharField(
        max_length=250,
        blank=True,
    )

    slug = models.SlugField(
        max_length=250,
        blank=True,
        unique=True,
    )

    geographical_scope = models.ForeignKey(GeographicalScope)

    observations = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['slug']

    def __unicode__(self):
        return u'%s, %s' % (self.full_name, self.organization.full_name)

    def save(self, *args, **kwargs):
        if not self.short_name:
            self.short_name = self.full_name.encode('utf-8')

        self.slug = slugify(self.short_name)

        super(FundingProgram, self).save(*args, **kwargs)


#########################
# Model: FundingProgramLogo
#########################

class FundingProgramLogo(models.Model):
    funding_program = models.ForeignKey(FundingProgram)

    logo = models.ImageField(
        upload_to=funding_program_logo_path,
        blank=True,
        null=True,
    )

    def __unicode__(self):
        return u'Logo for funding program: %s' % (self.funding_program.short_name)

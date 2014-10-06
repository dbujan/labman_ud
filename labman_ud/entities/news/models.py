# -*- encoding: utf-8 -*-

import requests
import tweetpony

from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from entities.core.models import BaseModel

from datetime import datetime
from redactor.fields import RedactorField


# Create your models here.

PROXY_DICT = {
    'http': settings.HTTP_PROXY,
    'https': settings.HTTPS_PROXY,
}


def post_tweet(title, slug):
    r = requests.get('%s%s%s' % (settings.KARMACRACY_URL, settings.NEWS_DETAIL_BASE_URL, slug), proxies=PROXY_DICT)

    short_link = r.text

    tweetpony_api = tweetpony.API(
        consumer_key=settings.TWEETPONY_CONSUMER_KEY,
        consumer_secret=settings.TWEETPONY_CONSUMER_SECRET,
        access_token=settings.TWEETPONY_ACCESS_TOKEN,
        access_token_secret=settings.TWEETPONY_ACCESS_TOKEN_SECRET
    )
    
    if len(settings.NEWS_CC) > 1:    
        cc = 'cc: %s' % (settings.NEWS_CC)
    else:
        cc = ''
        
    total_max_length = settings.NEWS_TITLE_MAX_LENGTH - len(cc)

    if len(title) >= total_max_length:
        tweet_title = '%s...' % (title[:total_max_length])
    else:
        tweet_title = title

    tweet = '%s: %s %s' % (tweet_title, short_link, cc)

    try:
        tweetpony_api.update_status(status=tweet)
    except tweetpony.APIError as err:
        print "Oops, something went wrong! Twitter returned error #%i and said: %s" % (err.code, err.description)


###########################################################################
# Model: New
###########################################################################

class News(BaseModel):
    title = models.CharField(
        max_length=250,
    )

    slug = models.SlugField(
        max_length=250,
        blank=True,
        unique=True,
    )

    content = RedactorField()

    created = models.DateTimeField(default=datetime.now, blank=True)

    tags = models.ManyToManyField('utils.Tag', through='NewsTag', related_name='news')
    projects = models.ManyToManyField('projects.Project', through='ProjectRelatedToNews', related_name='news')
    publications = models.ManyToManyField('publications.Publication', through='PublicationRelatedToNews', related_name='news')
    persons = models.ManyToManyField('persons.Person', through='PersonRelatedToNews', related_name='news')

    def __unicode__(self):
        return u'%s' % (self.title)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)

        if self.pk is None:
            post_tweet(self.title, self.slug)

        super(News, self).save(*args, **kwargs)


###########################################################################
# Model: NewsTag
###########################################################################

class NewsTag(BaseModel):
    tag = models.ForeignKey('utils.Tag')
    news = models.ForeignKey('News')

    def __unicode__(self):
        return u'%s tagged as: %s' % (self.news.title, self.tag.name)


###########################################################################
# Model: ProjectRelatedToNews
###########################################################################

class ProjectRelatedToNews(BaseModel):
    project = models.ForeignKey('projects.Project')
    news = models.ForeignKey('News')

    def __unicode__(self):
        return u'%s refers to project: %s' % (self.news.title, self.project.short_name)


###########################################################################
# Model: PublicationRelatedToNews
###########################################################################

class PublicationRelatedToNews(BaseModel):
    publication = models.ForeignKey('publications.Publication')
    news = models.ForeignKey('News')

    def __unicode__(self):
        return u'%s refers to project: %s' % (self.news.title, self.publication.title)


###########################################################################
# Model: PersonRelatedToNews
###########################################################################

class PersonRelatedToNews(BaseModel):
    person = models.ForeignKey('persons.Person')
    news = models.ForeignKey('News')

    def __unicode__(self):
        return u'%s refers to project: %s' % (self.news.title, self.person.full_name)


###########################################################################
# Model: EventRelatedToNews
###########################################################################

class EventRelatedToNews(BaseModel):
    event = models.ForeignKey('events.Event')
    news = models.ForeignKey('News')

    def __unicode__(self):
        return u'%s refers to event: %s' % (self.news.title, self.event.full_name)

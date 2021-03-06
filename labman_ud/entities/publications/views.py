# -*- encoding: utf-8 -*-

import threading
import weakref

# from django.template.defaultfilters import slugify
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from .forms import PublicationSearchForm
from .models import *

from entities.persons.models import Person
from entities.projects.models import Project, RelatedPublication
from entities.utils.models import Tag

from collections import OrderedDict, Counter

# Create your views here.

INDICATORS_TAG_SLUGS = ['isi', 'corea', 'coreb', 'corec', 'q1', 'q2', 'q3', 'q4']

PUBLICATION_TYPES = [
    'Book section', 'Book',
    'Conference paper', 'Proceedings',
    'Journal article', 'Journal',
    'Magazine article', 'Magazine',
    'Thesis'
]


###########################################################################
# View: publication_index
###########################################################################

def _validate_term(token, name, numeric=False):
    if not token.startswith(name):
        return False

    remainder = token[len(name):]
    if not remainder:
        return False

    if numeric:
        try:
            int(remainder)
        except:
            return False

    return True


def publication_index(request, tag_slug=None, publication_type=None, query_string=None):
    tag = None

    clean_index = False

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        publication_ids = PublicationTag.objects.filter(tag=tag).values('publication_id')
        publications = Publication.objects.filter(id__in=publication_ids).select_related('authors__author').prefetch_related('authors')

    if publication_type:
        publications = Publication.objects.filter(child_type=publication_type)

    if not tag_slug and not publication_type:
        clean_index = True
        publications = Publication.objects.all().select_related('authors__author').prefetch_related('authors')

    publications = publications.order_by('-year', '-title').exclude(authors=None)

    if request.method == 'POST':
        form = PublicationSearchForm(request.POST)
        if form.is_valid():
            query_string = form.cleaned_data['text']
            return HttpResponseRedirect(reverse('view_publication_query', kwargs={'query_string': query_string}))

    else:
        form = PublicationSearchForm()

    if query_string:
        # Given a query_string such as: author:"Oscar Pena" my "title word"; split in ['author:"Oscar Peña"','my','"title word"']
        initial_tokens = query_string.lower().split()
        tokens = []
        quotes_open = False
        current_token = ""
        for token in initial_tokens:
            if token.count('"') % 2 != 0:
                if quotes_open:
                    # Close quotes
                    current_token += " " + token
                    tokens.append(current_token)
                    quotes_open = False
                else:
                    current_token += token
                    quotes_open = True
            else:
                if quotes_open:
                    current_token += " " + token
                else:
                    tokens.append(token)
        if current_token:
            tokens.append(current_token)

        # Create filters that reduce the query size
        NUMERIC_FILTERS = {
            'year:': []
        }

        FILTERS = {
            'author:': [],
            'tag:': [],
            'title:': [],
        }

        special_tokens = []
        new_tokens = []  # E.g. 'author:"Aitor Almeida"' is converted to 'Aitor Almeida'
        for token in tokens:
            validated = False
            for word in FILTERS:
                if _validate_term(token, word):
                    special_tokens.append(token)
                    new_token = token[len(word):]
                    if new_token.startswith('"') and new_token.endswith('"'):
                        new_token = new_token[1:-1]
                    FILTERS[word].append(new_token)
                    new_tokens.append(new_token)
                    validated = True
                    break

            if not validated:
                for word in NUMERIC_FILTERS:
                    if _validate_term(token, word):
                        new_token = token[len(word):]
                        if new_token.startswith('"') and new_token.endswith('"'):
                            new_token = new_token[1:-1]
                        new_tokens.append(new_token)
                        NUMERIC_FILTERS[word].append(new_token)
                        special_tokens.append(token)
                        break

        search_terms = [token for token in tokens if token not in special_tokens] + new_tokens

        # Filter by publication
        if special_tokens:
            sql_query = Publication.objects.all()

            for year in NUMERIC_FILTERS['year:']:
                sql_query = sql_query.filter(year=int(year))

            for title in FILTERS['title:']:
                sql_query = sql_query.filter(title__icontains=title)

            if FILTERS['tag:']:
                for tag in FILTERS['tag:']:
                    tag_ids = PublicationTag.objects.filter(tag__name__icontains=tag).select_related('tag').values('tag__id')
                    sql_query = sql_query.filter(tags__id__in=tag_ids)

            if FILTERS['author:']:
                for author in FILTERS['author:']:
                    author_ids = PublicationAuthor.objects.filter(author__full_name__icontains=author).select_related('author').values('author__id')
                    sql_query = sql_query.filter(authors__id__in=author_ids)
        else:
            sql_query = Publication.objects.all()

        sql_query = sql_query.select_related('authors__author', 'tags__tag').prefetch_related('authors', 'tags', 'publicationauthor_set', 'publicationauthor_set__author')
        publication_strings = [(publication, publication.display_all_fields().lower()) for publication in sql_query]

        publications = []

        for publication, publication_string in publication_strings:
            matches = True

            for search_term in search_terms:
                if search_term not in publication_string:
                    matches = False
                    break

            if matches:
                publications.append(publication)

        clean_index = False

    publications_length = len(publications)

    last_created = Publication.objects.order_by('-log_created')[0]
    last_modified = Publication.objects.order_by('-log_modified')[0]

    publication_types = Publication.objects.all().exclude(authors=None).values_list('child_type', flat=True)

    counter = Counter(publication_types)
    ord_dict = OrderedDict(sorted(counter.items(), key=lambda t: t[1]))

    items = ord_dict.items()

    try:
        theses = Thesis.objects.all()

    except:
        theses = None

    # dictionary to be returned in render_to_response()
    return_dict = {
        'web_title': u'Publications',
        'clean_index': clean_index,
        'form': form,
        'last_created': last_created,
        'last_modified': last_modified,
        'publications': publications,
        'publication_type': publication_type,
        'publications_length': publications_length,
        'query_string': query_string,
        'tag': tag,
        'pubtype_info': dict(items),
        'theses': theses,
    }

    return render_to_response('publications/index.html', return_dict, context_instance=RequestContext(request))


###########################################################################
# View: publication_info
###########################################################################

def publication_info(request, slug):
    publication = get_object_or_404(Publication, slug=slug)
    return_dict = __build_publication_return_dict(publication)
    return_dict['current_tab'] = u'info'
    return_dict['web_title'] = publication.title
    return render_to_response('publications/info.html', return_dict, context_instance=RequestContext(request))


def publication_related_projects(request, slug):
    publication = get_object_or_404(Publication, slug=slug)
    return_dict = __build_publication_return_dict(publication)
    return_dict['current_tab'] = 'projects'
    return_dict['web_title'] = u'%s - Related projects' % publication.title
    return render_to_response('publications/related_projects.html', return_dict, context_instance=RequestContext(request))


def publication_related_publications(request, slug):
    publication = get_object_or_404(Publication, slug=slug)
    return_dict = __build_publication_return_dict(publication)
    return_dict['current_tab'] = 'publications'
    return_dict['web_title'] = u'%s - Related publications' % publication.title
    return render_to_response('publications/related_publications.html', return_dict, context_instance=RequestContext(request))


def __build_publication_return_dict(publication):
    author_ids = PublicationAuthor.objects.filter(publication=publication.id).values('author_id').order_by('position')
    authors = []

    for _id in author_ids:
        author = Person.objects.get(id=_id['author_id'])
        authors.append(author)

    related_projects_ids = RelatedPublication.objects.filter(publication=publication.id).values('project_id')
    related_projects = Project.objects.filter(id__in=related_projects_ids)

    related_publications_ids = RelatedPublication.objects.filter(project_id__in=related_projects_ids).values('publication_id')
    related_publications = Publication.objects.filter(id__in=related_publications_ids).exclude(id=publication.id)

    tag_ids = PublicationTag.objects.filter(publication=publication.id).values('tag_id')
    tags = Tag.objects.filter(id__in=tag_ids).order_by('name')

    tag_list = []
    indicators_list = []

    for tag in tags:
        if tag.slug in INDICATORS_TAG_SLUGS:
            indicators_list.append(tag)
        else:
            tag_list.append(tag)

    try:
        pdf = publication.pdf
    except:
        pdf = None

    parent_publication = None

    try:
        if publication.child_type == 'ConferencePaper':
            conference_paper = ConferencePaper.objects.get(slug=publication.slug)
            parent_publication = Proceedings.objects.get(id=conference_paper.parent_proceedings.id)

        if publication.child_type == 'JournalArticle':
            journal_article = JournalArticle.objects.get(slug=publication.slug)
            parent_publication = Journal.objects.get(id=journal_article.parent_journal.id)

        if publication.child_type == 'MagazineArticle':
            magazine_article = MagazineArticle.objects.get(slug=publication.slug)
            parent_publication = Magazine.objects.get(id=magazine_article.parent_magazine.id)

        if publication.child_type == 'BookSection':
            book_section = BookSection.objects.get(slug=publication.slug)
            parent_publication = Book.objects.get(id=book_section.parent_book.id)

    except:
        pass

    if publication.bibtex:
        bibtex = publication.bibtex.replace(",", ",\n")
    else:
        bibtex = None

    # dictionary to be returned in render_to_response()
    return {
        'authors': authors,
        'bibtex': bibtex,
        'indicators_list': indicators_list,
        'parent_publication': parent_publication,
        'pdf': pdf,
        'publication': publication,
        'related_projects': related_projects,
        'related_publications': related_publications,
        'tag_list': tag_list,
    }


###########################################################################
# View: publication_tag_cloud
###########################################################################

def publication_tag_cloud(request):
    tags = PublicationTag.objects.all().values_list('tag__name', flat=True)

    counter = Counter(tags)
    ord_dict = OrderedDict(sorted(counter.items(), key=lambda t: t[1]))

    items = ord_dict.items()
    items = items[len(items)-100:]

    # dictionary to be returned in render_to_response()
    return_dict = {
        'web_title': u'Publications tag cloud',
        'tag_dict': dict(items),
    }

    return render_to_response('publications/tag_cloud.html', return_dict, context_instance=RequestContext(request))


###########################################################################
# Feed: publications feeds
###########################################################################

class LatestPublicationsFeed(Feed):
    def __init__(self, *args, **kwargs):
        super(LatestPublicationsFeed, self).__init__(*args, **kwargs)
        self.__request = threading.local()

    title = "MORElab publications"
    description = "MORElab publications"

    def get_object(self, request):
        self.__request.request = weakref.proxy(request)
        return super(LatestPublicationsFeed, self).get_object(request)

    def link(self, obj):
        url = reverse('publication_index')
        return self.__request.request.build_absolute_uri(url)

    def items(self):
        return Publication.objects.order_by('-log_created')[:30]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.abstract

    def item_link(self, item):
        url = reverse('publication_info', args=[item.slug or 'no-slug-found'])
        return self.__request.request.build_absolute_uri(url)


###########################################################################
# View: phd_dissertations_index
###########################################################################

def phd_dissertations_index(request):
    theses = Thesis.objects.filter(author__is_active=True).order_by('-year', 'author__full_name')

    # dictionary to be returned in render_to_response()
    return_dict = {
        'web_title': u'PhD dissertations',
        'theses': theses,
    }

    return render_to_response('publications/phd_dissertations_index.html', return_dict, context_instance=RequestContext(request))

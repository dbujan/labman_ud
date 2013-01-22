# coding: utf-8

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from organization_manager.models import *
from organization_manager.forms import *

# Create your views here.

PAGINATION_NUMBER = 5


#########################
# View: organization_index
#########################

def organization_index(request):
    organizations = Organization.objects.all().order_by('name')
    paginator = Paginator(organizations, PAGINATION_NUMBER)

    page = request.GET.get('page')

    try:
        organizations = paginator.page(page)

    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        organizations = paginator.page(1)

    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        organizations = paginator.page(paginator.num_pages)

    return render_to_response("organization_manager/index.html", {
            "organizations": organizations,
        },
        context_instance = RequestContext(request))


#########################
# View: add_organization
#########################

def add_organization(request):
    if request.method == 'POST':
        form = OrganizationForm(request.POST, request.FILES)
        if form.is_valid():

            cd = form.cleaned_data

            name = cd['name']
            country = cd['country']
            homepage = cd['homepage']

            org = Organization(
                name = name.encode('utf-8'),
                country = country.encode('utf-8'),
                homepage = homepage.encode('utf-8'),
                logo = request.FILES['logo']
            )

            org.save()

            return HttpResponseRedirect("/organizaciones")
    else:
        form = OrganizationForm()

    return render_to_response("organization_manager/add.html", {
            "form": form,
        },
        context_instance = RequestContext(request))


#########################
# View: info_organization
#########################

def info_organization(request, slug):
    organization = get_object_or_404(Organization, slug = slug)

    return render_to_response("organization_manager/info.html", {
            "organization": organization,
        },
        context_instance = RequestContext(request))


#########################
# View: edit_organization
#########################

def edit_organization(request, slug):
    organization = get_object_or_404(Organization, slug = slug)

    if request.method == 'POST':
        form = OrganizationForm(request.POST, request.FILES)
        if form.is_valid():

            cd = form.cleaned_data

            organization.update()

            organization.name = cd['name'].encode('utf-8')
            organization.country = cd['country'].encode('utf-8')
            organization.homepage = cd['homepage'].encode('utf-8')
            organization.logo = request.FILES['logo']

            organization.save()

            return HttpResponseRedirect("/organizations")
    else:
        data = {
            'name': organization.name,
            'country': organization.country,
            'homepage': organization.homepage,
            'logo': organization.logo,
        }

        form = OrganizationForm(initial = data)

    return render_to_response("organization_manager/edit.html", {
            "organization": organization,
            "form": form,
        },
        context_instance = RequestContext(request))


#########################
# View: delete_organization
#########################

def delete_organization(request, slug):
    organization = get_object_or_404(Organization, slug = slug)
    organization.delete()

    return redirect('organization_index')

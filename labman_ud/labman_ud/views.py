# -*- encoding: utf-8 -*-

from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from entities.news.models import News


# Create your views here.


###########################################################################
# View: home
###########################################################################

def home(request):
    # dictionary to be returned in render_to_response()
    return_dict = {
        'latest_news': News.objects.order_by('-created')[:3]
    }

    return render_to_response('labman_ud/index.html', return_dict, context_instance=RequestContext(request))


###########################################################################
# View: logout
###########################################################################

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('home'))


###########################################################################
# View: about
###########################################################################

def about(request):
    return render_to_response('labman_ud/about.html', {'web_title': 'About'})


###########################################################################
# View: about_collaborations
###########################################################################

def about_collaborations(request):
    return render_to_response('labman_ud/about/collaborations.html', {'web_title': 'Collaborations'})


###########################################################################
# View: about_prototyping
###########################################################################

def about_prototyping(request):
    return render_to_response('labman_ud/about/prototyping.html', {'web_title': 'Prototyping'})


###########################################################################
# View: view404
###########################################################################

def view404(request):
    return render_to_response('labman_ud/404.html')

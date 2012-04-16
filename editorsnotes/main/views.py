from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
#from django.core.paginator import Paginator, InvalidPage
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from reversion import get_unique_for_object
from reversion.models import Revision
from urllib import urlopen
from models import *
from editorsnotes.djotero.utils import as_readable
import utils
import json
import re

def _sort_citations(instance):
    cites = { 'all': [] }
    for c in Citation.objects.filter(
        content_type=ContentType.objects.get_for_model(instance), 
        object_id=instance.id):
        cites['all'].append(c)
    cites['all'].sort(key=lambda c: c.ordering)
    return cites

@login_required
def index(request, project_slug=None):
    max_count = 6
    o = {}
    if project_slug:
        o['project'] = get_object_or_404(Project, slug=project_slug)
    for model in [Topic, Note, Document, Transcript]:
        model_name = model._meta.module_name
        if model_name == 'transcript':
            listname = 'document_list'
        else:
            listname = '%s_list' % model_name
        query_set = model.objects.order_by('-last_updated')
        if model == Document:
            # only get top-level documents
            query_set = query_set.filter(
                collection__isnull=True)
        if model == Transcript:
            # only get top-level documents
            query_set = query_set.filter(
                document__collection__isnull=True)
        if project_slug:
            query_set = query_set.filter(
                last_updater__userprofile__affiliation=o['project'])
        items = o.get(listname, [])
        items += list(query_set[:max_count])
        o[listname] = items
    o['document_list'] = sorted(o['document_list'],
                              key=lambda x: x.last_updated, 
                              reverse=True)[:max_count]
    return render_to_response(
        'index.html', o, context_instance=RequestContext(request))

@login_required
def all_topics(request, project_slug=None):
    o = {}
    if project_slug:
        o['project'] = get_object_or_404(Project, slug=project_slug)
    if 'type' in request.GET:
        o['type'] = request.GET['type']
        o['fragment'] = ''
        template = 'topic-columns.include'
    else:
        o['type'] = 'PER'
        template = 'all-topics.html'
    if project_slug:
        query_set = set([ ta.topic for ta in TopicAssignment.objects.filter(
            creator__userprofile__affiliation=o['project'],
            topic__type=o['type']) ])
    else:
        query_set = Topic.objects.filter(type=o['type'])
    [o['topics_1'], o['topics_2'], o['topics_3']] = utils.alpha_columns(
        query_set, 'slug', itemkey='topic')
    return render_to_response(
        template, o, context_instance=RequestContext(request))

@login_required
def all_documents(request, project_slug=None):
    o = {}
    if project_slug:
        o['project'] = get_object_or_404(Project, slug=project_slug)
    o['documents'] = []
    if project_slug:
        query_set = Document.objects.filter(
            last_updater__userprofile__affiliation=o['project'])
    else:
        query_set = Document.objects.all()
    # only get top-level documents
    query_set = query_set.filter(collection__isnull=True)
    for document in query_set:
        first_letter = document.ordering[0].upper()
        o['documents'].append(
            { 'document': document, 'first_letter': first_letter })
    return render_to_response(
        'all-documents.html', o, context_instance=RequestContext(request))

@login_required
def all_notes(request, project_slug=None):
    o = {}
    template = 'all-notes.html'
    o['filtered'] = False

    if request.GET.get('filter'):
        template = 'filtered-notes.html'
        o['filtered'] = True

    qs = SearchQuerySet().models(Note)
    query = []
    if request.GET.get('topic'):
        query += [ ' AND '.join([ 'related_topic_id:%s' % topic for topic
                                in request.GET.get('topic').split(',') ]) ]
    if request.GET.get('project'):
        query += [ ' AND '.join([ 'project_id:%s' % project for project
                                in request.GET.get('project').split(',') ]) ]
    qs = qs.narrow(' AND '.join(query)) if query else qs

    qs = qs.facet('related_topic_id').facet('project_id')
    facet_fields = qs.facet_counts()['fields']
    topic_facets = sorted(facet_fields['related_topic_id'],
                          key=lambda t: t[1], reverse=True)
    project_facets = sorted(facet_fields['project_id'],
                            key=lambda p: p[1], reverse=True)

    topic_facets = [ (Topic.objects.get(id=t_id), t_count)
                         for t_id, t_count in topic_facets[:16] ]
    o['topic_facets_1'] = topic_facets[:8]
    o['topic_facets_2'] = topic_facets[8:] if (len(topic_facets) > 8) else []

    o['project_facets'] = [ (Project.objects.get(id=p_id), p_count)
                           for p_id, p_count in project_facets ]
    o['notes'] = qs

    return render_to_response(
        template, o, context_instance=RequestContext(request)) 

@login_required
def topic(request, topic_slug):
    o = {}
    o['topic'] = get_object_or_404(Topic, slug=topic_slug)
    o['contact'] = { 'name': settings.ADMINS[0][0], 
                     'email': settings.ADMINS[0][1] }
    o['related_topics'] = o['topic'].related_topics.all()
    o['summary_cites'] = _sort_citations(o['topic'])
    notes = o['topic'].related_objects(Note)
    o['note_count'] = len(notes)
    note_topics = [ [ ta.topic for ta in n.topics.exclude(topic=o['topic']) ] for n in notes ]
    note_citations = [ _sort_citations(n) for n in notes ]
    o['notes'] = zip(notes, note_topics, note_citations)
    o['documents'] = o['topic'].related_objects(Document)
    for note, topics, citations in o['notes']:
       for cite in citations['all']:
           if not cite.document in o['documents']:
               cite.document.related_via = note
               o['documents'].append(cite.document)
    o['doc_count'] = len(o['documents'])
    o['thread'] = { 'id': 'topic-%s' % o['topic'].id, 'title': o['topic'].preferred_name }
    o['alpha'] = (request.user.groups.filter(name='Alpha').count() == 1)
    return render_to_response(
        'topic.html', o, context_instance=RequestContext(request))

@login_required
def note(request, note_id):
    o = {}
    o['note'] = get_object_or_404(Note, id=note_id)
    o['history'] = get_unique_for_object(o['note'])
    o['topics'] = [ ta.topic for ta in o['note'].topics.all() ]
    o['cites'] = _sort_citations(o['note'])
    return render_to_response(
        'note.html', o, context_instance=RequestContext(request))

def revision_to_dict(revision_id):
    # Content types for filtering
    note_ct = ContentType.objects.get_for_model(Note)
    topic_ct = ContentType.objects.get_for_model(TopicAssignment)
    cite_ct = ContentType.objects.get_for_model(Citation)

    revision_object = get_object_or_404(Revision, id=revision_id)
    revision_versions = revision_object.version_set

    revision = {
        'note': revision_versions.get(content_type=note_ct),
        'topics': revision_versions.filter(content_type=topic_ct),
        'cites': revision_versions.filter(content_type=cite_ct)
    }
    return revision

def note_at_revision(request, note_id, revision_id):
    base_note = get_object_or_404(Note, id=note_id)

    rev1 = revision_to_dict(revision_id)
    if not base_note == rev1['note'].object:
        return HttpResponseBadRequest()

    o = {}
    o['history'] = get_unique_for_object(base_note)
    o['revision_id'] = revision_id
    o['current_history_idx'] = o['history'].index(rev1['note'])

    if not request.GET.get('compare'):
        o['note'] = rev1['note'].object_version.object
        o['topics'] = [ ta.object.topic for ta in rev1['topics'] ]
        o['cites'] = {'all' : [ c.object_version.object for c in rev1['cites'] ]}

    else:
        o['note'] = base_note
        rev2 = revision_to_dict(request.GET.get('compare'))
        if not base_note == rev2['note'].object:
            return HttpResponseBadRequest()

        o['diffs'] = {}

        o['diffs']['note'] = utils.compare_elements(
            rev1['note'].field_dict['content'],
            rev2['note'].field_dict['content']
        )

        o['diffs']['cites'] = []
        rev1_cite_ids = []
        for cite1 in rev1['cites']:
            cited_document = Document.objects.get(id=cite1.field_dict['document'])
            cite2 = rev2['cites'].filter(object_id=cite1.object_id)
            if cite2:
                diff = utils.compare_elements(
                    cite1.field_dict['notes'],
                    cite2[0].field_dict['notes']
                )
            else:
                diff = utils.compare_elements(
                    cite1.field_dict['notes'],
                    ''
                )
            o['diffs']['cites'].append(
                {'document' : cited_document, 'diff' : diff})
            rev1_cite_ids.append(cite1.object_id)

        for cite in rev2['cites'].exclude(object_id__in=rev1_cite_ids):
            cited_document = Document.objects.get(id=cite.field_dict['document'])
            diff = utils.compare_elements(
                '',
                cite.field_dict['notes']
            )
            o['diffs']['cites'].append(
                {'document' : cited_document, 'diff' : diff})
        
    return render_to_response(
            'note.html', o, context_instance=RequestContext(request))
    
@login_required
def footnote(request, footnote_id):
    o = {}
    o['footnote'] = get_object_or_404(Footnote, id=footnote_id)
    o['thread'] = { 'id': 'footnote-%s' % o['footnote'].id, 
                    'title': o['footnote'].footnoted_text() }
    return render_to_response(
        'footnote.html', o, context_instance=RequestContext(request))

@login_required
def document(request, document_id):
    o = {}
    o['document'] = get_object_or_404(Document, id=document_id)
    o['topics'] = (
        [ ta.topic for ta in o['document'].topics.all() ] +
        [ c.content_object for c in o['document'].citations.filter(
                content_type=ContentType.objects.get_for_model(Topic)) ])
    o['scans'] = o['document'].scans.all()
    o['domain'] = Site.objects.get_current().domain
    notes = [ c.content_object for c in o['document'].citations.filter(
            content_type=ContentType.objects.get_for_model(Note)) ]
    o['notes'] = zip(notes, 
                     [ [ ta.topic for ta in n.topics.all() ] for n in notes ],
                     [ _sort_citations(n) for n in notes ])
    if o['document'].zotero_link():
        o['zotero_data'] = as_readable(o['document'].zotero_link().zotero_data)
        o['zotero_url'] = o['document'].zotero_link().zotero_url
        o['zotero_date_information'] = o['document'].zotero_link().date_information
    return render_to_response(
        'document.html', o, context_instance=RequestContext(request))

@login_required
def user(request, username=None):
    o = {}
    if not username:
        user = request.user
    else:
        user = get_object_or_404(User, username=username)
    if user.get_profile().zotero_uid and user.get_profile().zotero_key:
        o['zotero_status'] = True
    else:
        o['zotero_status'] = False
    o['profile'] = UserProfile.get_for(user)
    o['log_entries'], ignored = UserProfile.get_activity_for(user)
    return render_to_response(
        'user.html', o, context_instance=RequestContext(request))

def user_logout(request):
    logout(request)
    return render_to_response(
        'logout.html', context_instance=RequestContext(request))

reel_numbers = re.compile(r'(\S+):(\S+)')
ignored_punctuation = '!#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'

@login_required
def search(request):
    query = ''
    results = EmptySearchQuerySet()

    if request.GET.get('q'):
        query = request.GET.get('q')
        match = reel_numbers.search(query)
        if match:
            # so we can match reel numbers exactly
            query = reel_numbers.sub(r'"\1 \2"', query)
        def filter(c):
            if c in ignored_punctuation: return ' '
            return c
        query = ''.join([filter(c) for c in query])
        if len(query) > 0:
            results = SearchQuerySet().auto_query(query).load_all()
        if match:
            # restore the original form of the query so highlighting works
            query = query.replace('"%s %s"' % match.group(1,2), match.group(0))

    # paginator = Paginator(results, 20)
    
    # try:
    #     page = paginator.page(int(request.GET.get('page', 1)))
    # except InvalidPage:
    #     raise Http404('No such page of results!')
    
    o = {
        # 'page': page,
        # 'paginator': paginator,
        'results': results,
        'query': query,
    }
    
    return render_to_response(
        'search.html', o, context_instance=RequestContext(request))

def topic_to_dict(topic):
    return { 'preferred_name': topic.preferred_name,
             'id': topic.id,
             'uri': 'http://%s%s' % (Site.objects.get_current().domain, 
                                     topic.get_absolute_url()) } 

def api_topics(request):
    query = ''
    results = EmptySearchQuerySet()

    if request.GET.get('q'):
        query = ' AND '.join([ 'names:%s*' % term for term 
                               in request.GET.get('q').split() 
                               if len(term) > 1 ])
        results = SearchQuerySet().models(Topic).narrow(query).load_all()
    
    topics = [ topic_to_dict(r.object) for r in results ]
    return HttpResponse(json.dumps(topics), mimetype='text/plain')

def api_topic(request, topic_ids):
    topics_by_id = Topic.objects.in_bulk(topic_ids.split(','))
    topics = [ topic_to_dict(t) for t in topics_by_id.values() ]
    return HttpResponse(json.dumps(topics), mimetype='text/plain')

def document_to_dict(document):
    return { 'description': document.as_text(),
             'id': document.id,
             'uri': 'http://%s%s' % (Site.objects.get_current().domain, 
                                     document.get_absolute_url()) } 

def api_documents(request):
    query = ''
    results = EmptySearchQuerySet()

    if request.GET.get('q'):
        query = ' AND '.join([ 'title:%s*' % term for term 
                               in request.GET.get('q').split() 
                               if len(term) > 1 ])
        results = SearchQuerySet().models(Document).narrow(query).load_all()
    
    documents = [ document_to_dict(r.object) for r in results ]
    return HttpResponse(json.dumps(documents), mimetype='text/plain')

def api_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return HttpResponse(json.dumps(document_to_dict(document)), mimetype='text/plain')

def transcript_to_dict(transcript):
    return { 'description': transcript.as_text(),
             'id': transcript.id,
             'uri': 'http://%s%s' % (Site.objects.get_current().domain, 
                                     transcript.get_absolute_url()) } 

def api_transcripts(request):
    query = ''
    results = EmptySearchQuerySet()

    if request.GET.get('q'):
        query = ' AND '.join([ 'title:%s' % term for term 
                               in request.GET.get('q').split() 
                               if len(term) > 1 ])
        results = SearchQuerySet().models(Transcript).narrow(query).load_all()
    
    transcripts = [ transcript_to_dict(r.object) for r in results ]
    return HttpResponse(json.dumps(transcripts), mimetype='text/plain')

def api_transcript(request, transcript_id):
    transcript = get_object_or_404(Transcript, id=transcript_id)
    return HttpResponse(json.dumps(transcript_to_dict(transcript)), mimetype='text/plain')

# Proxy for cross-site AJAX requests. For development only.
def proxy(request):
    url = request.GET.get('url')
    if url is None:
        return HttpResponseBadRequest()
    if not url.startswith('http://cache.zoom.it/'):
        return HttpResponseForbidden()
    return HttpResponse(urlopen(url).read(), mimetype='application/xml')

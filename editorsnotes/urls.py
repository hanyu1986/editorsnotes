from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.forms import AuthenticationForm

admin.autodiscover()

urlpatterns = patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/profile/$', 'editorsnotes.main.views.user'),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^media/scans/(?P<path>.*)$', 'django.views.static.serve',
     { 'document_root': '/Users/ryanshaw/Code/editorsnotes/uploads/scans' }),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
     { 'document_root': '/Users/ryanshaw/Code/editorsnotes/editorsnotes/static' }),
)

from editorsnotes.main.views import SearchView

urlpatterns += patterns('editorsnotes.main.views',
    url(r'^$', 'index', name='index_view'),
    url(r'^topic/(?P<topic_slug>[-a-z0-9]+)/$', 'topic', name='topic_view'),
    url(r'^note/(?P<note_id>\d+)/$', 'note', name='note_view'),
    url(r'^user/(?P<username>[\w@\+\.\-]+)/$', 'user', name='user_view'),
    url(r'^source/(?P<source_id>\d+)/$', 'source', name='source_view'),
    url(r'^transcript/(?P<transcript_id>\d+)/$', 'transcript', name='transcript_view'),
    url(r'^search/', SearchView(), name='search_view'),
)

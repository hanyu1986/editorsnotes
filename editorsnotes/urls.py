from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.conf import settings
from django.views.generic.base import RedirectView
from editorsnotes.main.views import CustomBrowserIDVerify

admin.autodiscover()

urlpatterns = patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^accounts/profile/$', 'editorsnotes.main.views.user'),
    url(r'^accounts/browserid/$', CustomBrowserIDVerify.as_view(), name='browserid_verify'),
)

urlpatterns += patterns('',
    (r'^admin/', include('editorsnotes.admin_custom.urls')),
)

urlpatterns += patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),

    # The following won't actually be called in production, since Apache will intercept them.
    (r'^favicon.ico$', RedirectView.as_view(url='/static/style/icons/favicon.ico')),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.MEDIA_ROOT }),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', { 'document_root': settings.STATIC_ROOT }),
    (r'^proxy$', 'editorsnotes.main.views.proxy'),
)

urlpatterns += patterns('editorsnotes.main.views',
    url(r'^project/(?P<project_slug>[-_a-z0-9]+)/$', 'project', name='project_view'),
    url(r'^document/(?P<document_id>\d+)/$', 'document', name='document_view'),
    url(r'^topic/(?P<topic_slug>[\w\-,]+)/$', 'topic', name='topic_view'),
    url(r'^note/(?P<note_id>\d+)/$', 'note', name='note_view'),
    url(r'^user/(?P<username>[\w@\+\.\-]+)/$', 'user', name='user_view'),
    url(r'^logout/$', 'user_logout', name='user_logout_view'),
    url(r'^footnote/(?P<footnote_id>\d+)/$', 'footnote', name='footnote_view'),
    url(r'^search/$', 'search', name='search_view'),
)

api_patterns = patterns('editorsnotes.main.api_views',
    url(r'^api/topics/$', 'api_topics', name='api_topics_view'),
    url(r'^api/topics/(?P<topic_ids>\d+(,\d+)*)/$', 'api_topic', name='api_topic_view'),
    url(r'^api/documents/$', 'api_documents', name='api_documents_view'),
    url(r'^api/documents/(?P<document_id>\d+)/$', 'api_document', name='api_document_view'),
    url(r'^api/notes/$', 'api_notes', name='api_notes_view'),
    url(r'^api/transcripts/$', 'api_transcripts', name='api_transcripts_view'),
    url(r'^api/transcripts/(?P<transcript_id>\d+)/$', 'api_transcript', name='api_transcript_view'),
    url('^api2/', include('editorsnotes.api.urls')),
)

index_patterns = patterns('editorsnotes.main.views',
    url(r'^$', 'index', name='index_view'),
    url(r'^about/$', 'about', name='about_view'),
    url(r'^about/test/$', 'about_test'),
    url(r'^browse/$', 'browse', name='browse_view'),
    url(r'^documents/$', 'all_documents', name='all_documents_view'),
    url(r'^topics/$', 'all_topics', name='all_topics_view'),
    url(r'^notes/$', 'all_notes', name='all_notes_view'),
)

urlpatterns += api_patterns
urlpatterns += index_patterns

urlpatterns += patterns('editorsnotes.djotero.views',
    url(r'^document/upload/$', 'import_zotero', name='import_zotero_view'),
    url(r'^document/upload/libraries/$', 'libraries', name='libraries_view'),
    url(r'^document/upload/collections/$', 'collections', name='collections_view'),
    url(r'^document/upload/items/$', 'items', name='items_view'),
    url(r'^document/upload/continue/$', 'items_continue', name='items_continue_view'),
    url(r'^document/upload/import/$', 'import_items', name='import_items_view'),
    url(r'^user/zotero_info$', 'update_zotero_info', name='update_zotero_info_view'),
    url(r'^api/document/template/', 'zotero_template'),
    url(r'^api/document/blank/$', 'get_blank_item', name='get_blank_item_view'),
    url(r'^api/document/csl/$', 'zotero_json_to_csl', name='zotero_json_to_csl_view'),
    url(r'^api/document/archives/$', 'api_archives', name='api_archives_view'),
)
urlpatterns += patterns('editorsnotes.refine.views',
    url(r'^topics/clusters/$', 'show_topic_clusters', name='show_topic_clusters_view'),
    url(r'^topics/merge/(?P<cluster_id>\d+)/$', 'merge_topic_cluster', name='merge_topic_cluster_view'),
)

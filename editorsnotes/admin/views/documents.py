import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
import reversion

from editorsnotes.main.models import Document, Transcript

from common import BaseAdminView
from .. import forms

class DocumentAdminView(BaseAdminView):
    model = Document
    form_class = forms.DocumentForm
    formset_classes = (
        forms.TopicAssignmentFormset,
        forms.DocumentLinkFormset,
        forms.ScanFormset
    )
    template_name = 'document_admin.html'
    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.ajax_post(request, *args, **kwargs)
        return super(DocumentAdminView, self).post(request, *args, **kwargs)

    def get_object(self, document_id=None):
        return document_id and get_object_or_404(
            Document, id=document_id, project_id=self.project.id)

    def get_breadcrumb(self):
        breadcrumbs = (
            (self.project.name, self.project.get_absolute_url()),
            ('Documents', reverse('all_documents_view',
                               kwargs={'project_slug': self.project.slug})),
        )
        if self.object is None:
            breadcrumbs += (
                ('Add', None),
            )
        else:
            breadcrumbs += (
                (self.object.as_text(), self.object.get_absolute_url()),
                ('Edit', None)
            )
        return breadcrumbs

    def save_object(self, form, formsets):
        obj, action = super(DocumentAdminView, self).save_object(form, formsets)
        form.save_zotero_data()
        return obj, action

    def save_formset_form(self, form):
        obj = form.save(commit=False)
        obj.document = self.object
        obj.creator = self.request.user
        obj.save()
        return obj

    def ajax_post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        self.object = self.get_object()
        if self.object is not None:
            return HttpResponse(
                'Cannot save existing documents via ajax.', status=400)
        if form.is_valid():
            with reversion.create_revision():
                document = form.save(commit=False)
                document.creator = self.request.user
                document.last_updater = self.request.user
                document.project = self.project
                document.save()
                form.save_zotero_data()
            return HttpResponse(json.dumps(
                {'value': document.as_text(),
                 'id': document.id}
            ))
        else:
            return HttpResponse(json.dumps(form.errors), status=400)

class TranscriptAdminView(BaseAdminView):
    model = Transcript
    form_class = forms.TranscriptForm
    formset_classes = (
        forms.FootnoteFormset,
    )
    template_name = 'transcript_admin.html'
    def get(self, request, *args, **kwargs):
        response = super(TranscriptAdminView, self).get(request, *args, **kwargs)

        if isinstance(response, HttpResponseForbidden):
            return response

        footnote_fs = response.context_data['formsets']['footnote']
        if hasattr(self, 'object') and self.object is not None:
            footnote_ids = self.object.get_footnote_href_ids()
        else:
            footnote_ids = []

        footnote_fs.forms.sort(key=lambda fn: footnote_ids.index(fn.instance.id)
                               if fn.instance.id in footnote_ids else 9999)

        return response
    def get_object(self, document_id):
        self.document = get_object_or_404(
            Document, id=document_id, project_id=self.project.id)
        return self.document.transcript if self.document.has_transcript() else None
    def set_additional_object_properties(self, obj, form):
        obj.document = self.document
        return obj
    def save_object(self, form, formsets):
        obj = form.save(commit=False)
        action = 'add' if not obj.id else 'change'
        if action == 'add':
            obj.creator = self.request.user
            obj.document = self.document
        obj.last_updater = self.request.user
        obj.save()
        return obj, action
    def save_footnote_formset_form(self, form):
        footnote = form.save(commit=False)
        transcript = self.object
        stamp = form.cleaned_data.get('stamp', None)

        if not footnote.id:
            footnote.transcript = transcript
            footnote.creator = self.request.user
        footnote.last_updater = self.request.user
        footnote.save()

        if stamp:
            a = transcript.content.cssselect('a.footnote[href$="%s"]' % stamp)[0]
            a.attrib['href'] = footnote.get_absolute_url()
            transcript.save()
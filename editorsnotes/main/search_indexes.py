# -*- coding: utf-8 -*-

import json

from haystack import indexes

from editorsnotes.djotero.utils import get_creator_name

from models.documents import Document, Footnote, Transcript
from models.notes import Note
from models.topics import TopicNode

class DocumentIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='as_text')
    text = indexes.CharField(document=True, use_template=True)
    autocomplete = indexes.EdgeNgramField(model_attr='description')
    project = indexes.CharField(model_attr='project')
    project_slug = indexes.MultiValueField(faceted=True)

    related_topic_id = indexes.MultiValueField(faceted=True)
    representations = indexes.MultiValueField(faceted=True)

    # Zotero fields
    creators = indexes.MultiValueField(faceted=True)
    archive = indexes.CharField(faceted=True)
    itemType = indexes.CharField(faceted=True)
    publicationTitle = indexes.CharField(faceted=True)
    def get_model(self):
        return Document
    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(import_id__startswith='inglis')

    def prepare_related_topic_id(self, obj):
        return [t.id for t in obj.get_all_related_topics()]
    def prepare_representations(self, obj):
        return [r for r in obj.get_all_representations()]
    def prepare_project_slug(self, obj):
        return [obj.project.slug]
    def prepare(self, obj):

        self.prepared_data = super(DocumentIndex, self).prepare(obj)

        zotero_data = json.loads(obj.zotero_data) \
                if obj.zotero_data is not None else {}

        for field in ['archive', 'publicationTitle', 'itemType']:
            if field in zotero_data:
                self.prepared_data[field] = zotero_data[field]
            elif field == 'itemType':
                self.prepared_data[field] = 'none'

        names = []
        if zotero_data.get('creators'):
            for c in zotero_data['creators']:
                creator = get_creator_name(c)
                names.append(creator)
        self.prepared_data['creators'] = [n for n in names if n]

        return self.prepared_data


class TranscriptIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='as_text')
    text = indexes.CharField(document=True, use_template=True)
    def get_model(self):
        return Transcript
    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(
            document__import_id__startswith='inglis')

class FootnoteIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='as_text')
    text = indexes.CharField(document=True, use_template=True)
    def get_model(self):
        return Footnote

class TopicIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='as_text')
    text = indexes.CharField(document=True, use_template=True)
    autocomplete = indexes.EdgeNgramField(model_attr='_preferred_name')
    names = indexes.CharField(use_template=True)
    project = indexes.MultiValueField()
    project_slug = indexes.MultiValueField(faceted=True)
    related_topic_id = indexes.MultiValueField(faceted=True)
    def get_model(self):
        return TopicNode
    def index_queryset(self, using=None):
        return self.get_model().objects.select_related('project_containers__project')
    def prepare_project(self, obj):
        return [pc.project.name for pc in obj.project_containers.all()]
    def prepare_project_slug(self, obj):
        return [pc.project.slug for pc in obj.project_containers.all()]
    def prepare_related_topic_id(self, obj):
        return [ta.id for ta in obj.related_objects(model=TopicNode)]

class NoteIndex(indexes.SearchIndex, indexes.Indexable):
    title = indexes.CharField(model_attr='as_text')
    text = indexes.CharField(document=True, use_template=True)
    autocomplete = indexes.EdgeNgramField(model_attr='title')
    project = indexes.CharField(model_attr='project')
    project_slug = indexes.MultiValueField(faceted=True)
    related_topic_id = indexes.MultiValueField(faceted=True)
    last_updated = indexes.DateTimeField(model_attr='last_updated')
    def get_model(self):
        return Note
    def index_queryset(self, using=None):
        return self.get_model().objects.select_related('project')
    def prepare_project_slug(self, obj):
        return [obj.project.slug]
    def prepare_related_topic_id(self, obj):
        return [t.topic.id for t in obj.topics.all()]

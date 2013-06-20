from django.core.urlresolvers import NoReverseMatch
from lxml import etree

from rest_framework import serializers
from rest_framework.relations import RelatedField, HyperlinkedRelatedField
from rest_framework.reverse import reverse

from editorsnotes.main.models.notes import (
    Note, TextNS, CitationNS, NoteReferenceNS)

class HyperLinkedDocumentField(HyperlinkedRelatedField):
    def to_native(self, obj):
        """
        Return URL from document
        """
        try:
            return reverse(
                self.view_name, args=[obj.project.slug, obj.id],
                request=self.context.get('request', None),
                format=self.format or self.context.get('format', None))
        except NoReverseMatch:
            raise Exception('Could not resolve URL for document.')

class TextNSSerializer(serializers.ModelSerializer):
    section_id = serializers.Field(source='note_section_id')
    section_type = serializers.Field(source='section_type_label')
    class Meta:
        model = TextNS
        fields = ('section_id', 'section_type', 'content',)

class CitationNSSerializer(serializers.ModelSerializer):
    section_id = serializers.Field(source='note_section_id')
    note_id = serializers.Field(source='note_id')
    section_type = serializers.Field(source='section_type_label')
    document = HyperLinkedDocumentField(view_name = 'api:api-documents-detail')
    document_description = serializers.SerializerMethodField('get_document_description')
    class Meta:
        model = CitationNS
        fields = ('note_id', 'section_id', 'section_type',
                  'document', 'document_description', 'content',)
    def get_document_description(self, obj):
        return etree.tostring(obj.document.description)

class NoteReferenceNSSerializer(serializers.ModelSerializer):
    section_id = serializers.Field(source='note_section_id')
    section_type = serializers.Field(source='section_type_label')
    note_reference = HyperlinkedRelatedField(view_name='api:api-notes-detail')
    note_reference_title = serializers.SerializerMethodField(
        'get_referenced_note_title')
    class Meta:
        model = NoteReferenceNS
        fields = ('section_id', 'section_type', 'note_reference',
                  'note_reference_title', 'content',)
    def get_referenced_note_title(self, obj):
        return obj.note_reference.title

def _serializer_from_section_type(section_type):
    if section_type == 'citation':
        serializer = CitationNSSerializer
    elif section_type == 'text':
        serializer = TextNSSerializer
    elif section_type == 'notereference':
        serializer = NoteReferenceNSSerializer
    else:
        raise NotImplementedError(
            'No such note section type: {}'.format(section_type))
    return serializer

class NoteSectionField(serializers.RelatedField):
    def field_to_native(self, note, field_name):
        qs = note.sections.select_subclasses()\
                .select_related('citationns__document__project',
                                'notereferencens__note__project')
        return [self.to_native(section) for section in qs.all()]
    def to_native(self, section):
        section_type = getattr(section, '_section_type')
        serializer_class = _serializer_from_section_type(
            section.section_type_label)
        serializer = serializer_class(section)
        return serializer.data

class SectionOrderingField(serializers.WritableField):
    def section_ids(self, note):
        if not hasattr(self, '_section_ids'):
            self._section_ids = [
                ns.note_section_id for ns in note.sections.all()
            ]
        return self._section_ids
    def field_to_native(self, obj, field_name):
        return self.section_ids(obj)
    def field_from_native(self, data, files, field_name, into):
        note = self.root.object

        if not data.has_key(field_name):
            data[field_name] = self.section_ids(note)

        ids = data.get(field_name, None)

        if not isinstance(ids, list):
            raise serializers.ValidationError('Must be a list')

        different_ids = set.symmetric_difference(
            set(ids), set(self.section_ids(note)))

        if len(different_ids):
            raise serializers.ValidationError(
                'Must contain every section id and no more')

        for section in note.sections.all():
            section.ordering = data[field_name].index(section.note_section_id)
            section.save()

        # we don't need to update the "into" dict, because nothing changed.
        # The section_ordering list doesn't map to a native object.

        return 


class NoteSerializer(serializers.ModelSerializer):
    topics = RelatedField('topics', many=True)
    section_ordering = SectionOrderingField()
    sections = NoteSectionField(many=True)
    class Meta:
        model = Note
        fields = ('id', 'title', 'topics', 'content', 'status', 
                  'section_ordering', 'sections',)

class MinimalNoteSerializer(serializers.ModelSerializer):
    topics = RelatedField('topics', many=True)
    class Meta:
        model = Note
        fields = ('id', 'title', 'topics', 'content', 'status',)

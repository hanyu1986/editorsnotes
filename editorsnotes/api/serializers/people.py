from rest_framework import serializers
from rest_framework.reverse import reverse

from editorsnotes.main.models import Project, User

class ProjectSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField('get_api_url')
    notes = serializers.SerializerMethodField('get_notes_url')
    topics = serializers.SerializerMethodField('get_topics_url')
    documents = serializers.SerializerMethodField('get_documents_url')
    class Meta:
        model = Project
        fields = ('slug', 'name', 'url', 'notes', 'topics', 'documents',)
    def get_api_url(self, obj):
        return reverse('api:api-project-detail', args=(obj.slug,),
                       request=self.context['request'])
    def get_notes_url(self, obj):
        return reverse('api:api-notes-list', args=(obj.slug,),
                       request=self.context['request'])
    def get_topics_url(self, obj):
        return reverse('api:api-topics-list', args=(obj.slug,),
                       request=self.context['request'])
    def get_documents_url(self, obj):
        return reverse('api:api-documents-list', args=(obj.slug,),
                       request=self.context['request'])

class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.Field('display_name')
    projects = serializers.SerializerMethodField('get_project_affiliation')
    class Meta:
        model = User
        fields = ('username', 'display_name', 'last_login', 'projects',)
    def get_project_affiliation(self, obj):
        return [{
            'name': project.name,
            'url': reverse('api:api-project-detail', args=(project.slug,),
                           request=self.context['request'])
        } for project in obj.get_affiliated_projects()]

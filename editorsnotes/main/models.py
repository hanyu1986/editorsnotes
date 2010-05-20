# -*- coding: utf-8 -*-

import re
import utils
import fields
from copy import deepcopy
from lxml import etree
from unaccent import unaccent
from django.db import models
from django.contrib.auth.models import User
from django.core import urlresolvers

class CreationMetadata(models.Model):
    creator = models.ForeignKey(User, editable=False, related_name='created_%(class)s_set')
    created = models.DateTimeField(auto_now_add=True)
    def created_display(self):
        return utils.timeago(self.created)
    created_display.allow_tags = True
    created_display.short_description = 'created'
    created_display.admin_order_field = 'created'
    class Meta:
        abstract = True
        get_latest_by = 'created'

class Note(CreationMetadata):
    u""" 
    Text written by an editor or curator. The text is stored as XHTML,
    so it may have hyperlinks and all the other features that XHTML
    enables.

    'type' indicates whether this is a 'query' (asking something) or a
    'note' (explaining or describing something).

    Style elements are stripped from content.
    >>> user = User.objects.create_user('tester', '', 'testerpass')
    >>> note = Note.objects.create(content=u'<style>garbage</style><h1>hey</h1><p>this is a <em>note</em></p>', creator=user, last_updater=user)
    >>> note.content_as_html()
    '<div><h1>hey</h1><p>this is a <em>note</em></p></div>'
    >>> note.type
    u'N'

    Add references.
    >>> note.references.create(citation='<p><span class="title">Anarchism and other essays</span>, 3rd edition, 1917</p>', url='http://books.google.com/books?id=U5ZYAAAAMAAJ', creator=user)
    <Reference: Reference object>

    Add citations.
    >>> source = Source.objects.create(description='Ryan Shaw, <em>My Big Book of Cool Stuff</em>, 2010.', type='P', creator=user)
    >>> note.citations.create(source=source, location='98-113', creator=user)
    <Citation: Citation object>
    >>> note.citations.all()
    [<Citation: Citation object>]

    Assign terms.
    >>> term = Term.objects.create(preferred_name=u'Example', creator=user)
    >>> TermAssignment.objects.create(note=note, term=term, creator=user)
    <TermAssignment: Example>
    >>> note.terms.all()
    [<Term: Example>]
    >>> term.note_set.all()
    [<Note: hey this is a note>]
    
    Can't assign the same term more than once.
    >>> TermAssignment.objects.create(note=note, term=term, creator=user)
    Traceback (most recent call last):
    IntegrityError: duplicate key value violates unique constraint "main_termassignment_term_id_346a14e0_uniq"
    <BLANKLINE>
    """
    content = fields.XHTMLField()
    type = models.CharField(max_length=1, choices=(('N','note'),('Q','query')), default='N')
    terms = models.ManyToManyField('Term', through='TermAssignment')
    last_updater = models.ForeignKey(User, editable=False, related_name='last_to_update_note_set')
    last_updated = models.DateTimeField(auto_now=True)
    def content_as_html(self):
        return etree.tostring(self.content)
    def last_updated_display(self):
        return utils.timeago(self.last_updated)
    last_updated_display.allow_tags = True
    last_updated_display.short_description = 'last updated'
    last_updated_display.admin_order_field = 'last_updated'
    def edit_history(self):
        return u'Created by %s %s. Last edited by %s %s.' % (
            UserProfile.get_for(self.creator).name_display(), 
            self.created_display(), 
            UserProfile.get_for(self.last_updater).name_display(),
            self.last_updated_display())
    edit_history.allow_tags = True
    def excerpt(self):
        return utils.truncate(utils.xhtml_to_text(self.content))
    def __unicode__(self):
        return self.excerpt()
    def get_absolute_url(self):
        return '/n/%s/' % self.id
    def get_admin_url(self):
        return urlresolvers.reverse('admin:main_note_change', args=(self.id,))
    class Meta:
        ordering = ['-last_updated']  

class Reference(CreationMetadata):
    u"""
    A bibliographic citation (as XHTML) and reference to a document.
    """
    note = models.ForeignKey(Note, related_name='references')
    citation = fields.XHTMLField()
    type = models.CharField(max_length=1, choices=(('P','primary source'),('S','secondary source')), default='S')
    ordering = models.CharField(max_length=5, editable=False)
    url = models.URLField(blank=True, verify_exists=True)
    def citation_as_html(self):
        if self.url:
            e = deepcopy(self.citation)
            a = etree.SubElement(e, 'a')
            a.href = self.url
            a.text = self.url
            a.getprevious().tail += ' '
            return etree.tostring(e)
        else:
            return etree.tostring(self.citation)
    def save(self, *args, **kwargs):
        self.ordering = utils.xhtml_to_text(self.citation)[:5]
        super(Reference, self).save(*args, **kwargs)
    class Meta:
        ordering = ['type','ordering']    

class Source(CreationMetadata):
    u"""
    A documented source for assertions made in notes. 
    """
    description = fields.XHTMLField()
    type = models.CharField(max_length=1, choices=(('P','primary source'),('S','secondary source')), default='S')
    ordering = models.CharField(max_length=32, editable=False)
    url = models.URLField(blank=True, verify_exists=True)
    def description_as_html(self):
        if self.url:
            e = deepcopy(self.description)
            a = etree.SubElement(e, 'a')
            a.href = self.url
            a.text = self.url
            a.getprevious().tail += ' '
            return etree.tostring(e)
        else:
            return etree.tostring(self.description)
    def save(self, *args, **kwargs):
        self.ordering = utils.xhtml_to_text(self.description)[:32]
        super(Source, self).save(*args, **kwargs)
    def __unicode__(self):
        return u'%s...' % self.ordering
    class Meta:
        ordering = ['type','ordering']    

class Citation(CreationMetadata):
    u"""
    A reference to or citation of a documented source. Links notes and sources.
    """
    note = models.ForeignKey(Note, related_name='citations')
    source = models.ForeignKey(Source, related_name='citations')
    locator = models.CharField(max_length=16, blank=True)

class Term(CreationMetadata):
    u""" 
    A controlled term such as a person name, an organization name, a
    place name, an event name, a publication name, or the name of a
    topic or theme.

    >>> term = Term(preferred_name=u'Foote, Edward B. (Edward Bliss) 1829-1906')
    >>> term.make_slug()
    u'foote-edward-b-edward-bliss-1829-1906'

    >>> term = Term(preferred_name=u'Räggler å paschaser på våra mål tå en bonne')
    >>> term.make_slug()
    u'raggler-a-paschaser-pa-vara-mal-ta-en-bonne'
    """
    preferred_name = models.CharField(max_length='80', unique=True)
    slug = models.CharField(max_length='80', unique=True, editable=False)
    def make_slug(self):
        return '-'.join(
            [ x for x in re.split('\W+', unaccent(self.__unicode__()))
              if len(x) > 0 ]).lower()
    def save(self, *args, **kwargs):
        self.slug = self.make_slug()
        super(Term, self).save(*args, **kwargs)
    def __unicode__(self):
        return self.preferred_name
    #@models.permalink
    def get_absolute_url(self):
        return '/t/%s/' % self.slug
        #return ('term_view', (), { 'slug': self.slug })
    class Meta:
        ordering = ['preferred_name']

class Alias(CreationMetadata):
    u"""
    An alternate name for a term.
    """
    term = models.ForeignKey(Term, related_name='aliases')
    name = models.CharField(max_length='80')
    def __unicode__(self):
        return self.name
    class Meta(CreationMetadata.Meta):
        unique_together = ('term', 'name')
        verbose_name_plural = 'aliases'

class TermAssignment(CreationMetadata):
    u""" 
    An assignment of a term to a note.
    """
    term = models.ForeignKey(Term)
    note = models.ForeignKey(Note, related_name='notes')
    def __unicode__(self):
        return self.term.preferred_name
    class Meta(CreationMetadata.Meta):
        unique_together = ('term', 'note')
        verbose_name_plural = 'index terms'

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    def get_absolute_url(self):
        return '/u/%s/' % self.user.username
    def _get_display_name(self):
        "Returns the full name if available, or the username if not."
        display_name = self.user.username
        if self.user.first_name:
            display_name = self.user.first_name
            if self.user.last_name:
                display_name = '%s %s' % (self.user.first_name, self.user.last_name)
        return display_name
    display_name = property(_get_display_name)
    def last_login_display(self):
        return utils.timeago(self.user.last_login)
    last_login_display.allow_tags = True
    def name_display(self):
        return '<a class="subtle" href="%s">%s</a>' % (self.get_absolute_url(), self.display_name)
    name_display.allow_tags = True
    @staticmethod
    def get_for(user):
        try:
            return user.get_profile()
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(user=user)




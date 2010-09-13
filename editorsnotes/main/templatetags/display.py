from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from editorsnotes.main import utils
from editorsnotes.main.models import UserProfile
from isodate import datetime_isoformat
from lxml import etree

register = template.Library()

@register.filter
def as_text(tree):
    return utils.xhtml_to_text(tree)

@register.filter
def as_html(tree):
    return mark_safe(etree.tostring(tree))

@register.filter
def display_user(user, autoescape=None):
    profile = UserProfile.get_for(user)
    esc = autoescape and conditional_escape or (lambda x: x)
    return mark_safe(
        '<a class="user-link" href="%s">%s</a>' % (
            profile.get_absolute_url(), esc(profile.display_name)))
display_user.needs_autoescape = True

@register.filter
def timeago(datetime):
    return mark_safe(
        '<time class="timeago" datetime="%s">%s</time>' % (
            datetime_isoformat(datetime), datetime.strftime('%I:%M%p, %b %d %Y')))

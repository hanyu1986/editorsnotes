import json
import os

from django import template
from django.conf import settings

register = template.Library()

@register.tag
def make_backbone_templates(parser, token):
    try:
        tag_name, backbone_templates_path = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            u'{} tag requires single argument (string of directory name)'\
            .format(token.contents.split()[0]))

    templates_dir = os.path.join(settings.STATIC_ROOT,
                                 backbone_templates_path[1:-1])

    if not os.path.exists(templates_dir):
        raise template.TemplateSyntaxError(
            u'Argument for {} must be a valid directory within the static_files'
            ' directory. If this directory ({}) should exist, try running '
            '`./manage.py collectstatic`.'.format(tag_name, templates_dir))

    return BackboneTemplateNode(templates_dir)

class BackboneTemplateNode(template.Node):
    def __init__(self, templates_dir):
        self.templates_dir = templates_dir

    def file_to_template(self, filename):
        template_name, _ = os.path.splitext(filename)
        with open(os.path.join(self.templates_dir, filename)) as template_file:
            template_text = template_file.read().replace('\n', '')
        return "EditorsNotes.Templates['{}'] = _.template({});".format(
            template_name, json.dumps(template_text))

    def render(self, context):
        templates = [
            self.file_to_template(filename) for filename in
            os.listdir(self.templates_dir)
            if filename.endswith( ('html', 'htm', 'txt',) )
        ]
        return '<script type="text/javascript">\n{}\n</script>'.format(
            '\n'.join(templates))

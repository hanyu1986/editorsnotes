from django.core.management.base import BaseCommand, CommandError
from reversion.models import Version
from collections import defaultdict
from optparse import make_option
import json

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-l', '--list-dead-fields',
            action='store_true',
            dest='list_fields',
            default=False,
            help='Return a list of deprecated fields, with their models'),
        make_option('-d', '--delete-dead-fields',
            action='store_true',
            dest='delete_fields',
            default=False,
            help='Update old revisions by deleting deprecated fields'),
        make_option('-u', '--update-required-fields',
            action='store_true',
            dest='update_fields',
            default=False,
            help='Update old revisions by providing values for newly-created required fields.'),
    )

    def handle(self, *args, **options):
        
        object_fields = {}
        new_fields_dict = defaultdict(dict)
        deprecated_fields_dict = defaultdict(set)
        updated_counter = 0

        for v in Version.objects.all():

            if not v.object:
                continue

            object_name = v.object._meta.object_name
            v_data = json.loads(v.serialized_data)

            if not object_fields.has_key(object_name):
                fields = v.object._meta.get_all_field_names()
                object_fields[object_name] = fields

            current_fields = object_fields[object_name]
            version_fields = v_data[0]['fields']
            bad_fields = [f for f in version_fields if f not in current_fields]

            for bad_field in bad_fields:
                deprecated_fields_dict[object_name].add(bad_field)

            if options['list_fields']:
                new_model_fields = list(set.difference(
                    set(current_fields), set(version_fields)))
                if not new_fields_dict.has_key(object_name):
                    # Check each newly created field for 'blank=False'
                    new_fields_for_obj = []
                    for f in new_model_fields:
                        nf = v.object._meta.get_field_by_name(f)[0]
                        if hasattr(nf, 'blank') and not nf.blank:
                            new_fields_for_obj.append(f)

                    new_fields_dict[object_name] = new_fields_for_obj

            elif options['delete_fields']:
                for field_to_remove in bad_fields:
                    del(v_data[0]['fields'][field_to_remove])
                v.serialized_data = json.dumps(v_data)
                v.save()
                updated_counter += 1


        deprecated_fields = ['%s: %s' % ( obj, ', '.join(list(fields)) )
                             for obj, fields in deprecated_fields_dict.items()]
        new_fields = ['%s: %s' % ( obj, ', '.join(fields) )
                      for obj, fields in new_fields_dict.items() if fields]

        if options['list_fields']: 
            self.stderr.write('\nDeprecated fields by version model:\n%s\n' % (
                '\n'.join(deprecated_fields) or 'None'))
            self.stderr.write('\nNew required fields by version model:\n%s\n\n' % (
                '\n'.join(new_fields) or 'None'))
        elif options['delete_fields']:
            self.stderr.write('\nDeprecated fields by version model:\n%s\n' % (
                '\n'.join(deprecated_fields)))
            self.stderr.write('\n%s version models updated\n' % updated_counter)
        if options['update_fields']:
            pass

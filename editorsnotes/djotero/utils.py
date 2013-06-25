import json
import re
from collections import Counter, OrderedDict
from urllib2 import urlopen, HTTPError, Request

from lxml import etree
import requests

from django.core.cache import cache

NS = {'xhtml': 'http://www.w3.org/1999/xhtml',
      'zot' : "http://zotero.org/ns/api",
      'atom' : "http://www.w3.org/2005/Atom"}

ZOTERO_BASE_URL = 'https://api.zotero.org'

def validate_zotero_data(zotero_dict):
    item_type = zotero_dict.has_key('itemType') and len(zotero_dict['itemType'])
    populated_fields = [ v for v in zotero_dict.values()
                               if isinstance(v, basestring) and v ]

    if all([item_type, len(populated_fields) > 1]):
        return True
    else:
        return False

# Zotero API calls
def get_libraries(zotero_uid, zotero_key):
    url = '/users/%s/groups?key=%s' % (zotero_uid, zotero_key)
    access = {'zapi_version' : 'null',
              'libraries' : [{'title' : 'Your library',
                              'location': '/users/%s' % (zotero_uid) }]}
    for x in parse_xml(url)['items']:
        title = x.xpath('./atom:title', namespaces=NS)[0].text
        loc = x.xpath('./atom:link[@rel="self"]', namespaces=NS)[0].attrib['href'].replace(ZOTERO_BASE_URL, '')
        access['libraries'].append({'title' : title, 'location' : loc })
    return access

def get_item_types():
    url = ZOTERO_BASE_URL + '/itemTypes'
    if not cache.get('item_types'):
        resp = urlopen(url)
        data = resp.read()
        resp.close()
        cache.set('item_types', data, 60 * 24 * 7)
    data = json.loads(cache.get('item_types'))

    from editorsnotes.main.models import Document
    from haystack.query import SearchQuerySet
    used_item_types = SearchQuerySet()\
            .models(Document)\
            .exclude(itemType='none')\
            .values_list('itemType', flat=True)

    return {
        'itemTypes': data,
        'common': sorted(
            [typ[0] for typ in Counter(used_item_types).most_common()[:10]])
    }

def get_collections(zotero_key, loc, top):
    if top:
        url = '%s/collections/top?key=%s&order=title&format=atom&content=json' % (loc, zotero_key)
    else:
        url = '%s/collections?key=%s&format=atom&content=json' % (loc, zotero_key)
    collections = { 'zapi_version' : 'null',
                    'collections' : []}
    for x in parse_xml(url)['items']:
        title = x.xpath('./atom:title', namespaces=NS)[0].text
        loc = x.xpath('./atom:link[@rel="self"]', namespaces=NS)[0].attrib['href'].replace(ZOTERO_BASE_URL, '')
        has_children = bool(int(x.xpath('./zot:numCollections', namespaces=NS)[0].text))
        collections['collections'].append({ 'title' : title, 'location' : loc, 'has_children' : int(has_children) })
    return collections

def get_items(zotero_key, loc, opts):
    opts = ['%s=%s' % (key, str(opts[key])) for key in opts.keys()]
    url = '%s/items?key=%s&format=atom&content=json&%s' % (loc, zotero_key, '&'.join(opts))
    latest = { 'zapi_version' : 'null', 'items' : []}
    parsed = parse_xml(url)
    latest['total_items'] = parsed['count']
    for x in parsed['items']:
        title = x.xpath('./atom:title', namespaces=NS)[0].text
        library_url = x.xpath('./atom:id', namespaces=NS)[0].text
        item_id = x.xpath('./zot:key', namespaces=NS)[0].text
        item_json = x.xpath('./atom:content[@zot:type="json"]', namespaces=NS)[0].text
        try:
            item_date = json.loads(item_json)['date']
        except:
            item_date = ""
        if json.loads(item_json)['itemType'] not in ['note', 'attachment']:
            citeproc_identifier = library_url[library_url.rindex('items') + 6:]
            item_csl = as_csl(item_json, citeproc_identifier)
            latest['items'].append(
                {'title' : title,
                 'item_type' : type_map['readable'][json.loads(item_json)['itemType']],
                 'loc' : loc,
                 'id' : item_id,
                 'date' : item_date,
                 'url' : library_url,
                 'item_json' : item_json,
                 'item_csl' : item_csl })
    return latest

def get_item_template(item_type):
    if not cache.get('item_template_%s' % item_type):
        url = '%s/items/new?itemType=%s' % (ZOTERO_BASE_URL, item_type)
        page = urlopen(url)
        new_item = page.read()
        cache.set('item_template_%s' % item_type, new_item, 60 * 24 * 7)
    return cache.get('item_template_%s' % item_type)

def get_creator_types(item_type):
    if not cache.get('creators_%s' % item_type):
        url = '%s/itemTypeCreatorTypes?itemType=%s' % (ZOTERO_BASE_URL, item_type)
        page = urlopen(url)
        creators = page.read()
        cache.set('creators_%s' % item_type, creators, 60 * 24 * 7)
    return cache.get('creators_%s' % item_type)

# Helper functions
def as_csl(zotero_json_string, citeproc_identifier):
    zotero_data = json.loads(zotero_json_string)
    
    output = {}
    output['type'] = type_map['csl'][zotero_data['itemType']]
    output['id'] = citeproc_identifier # For use with citeproc-js.
    
    # Translate fields for CSL processing
    zotero_fields = zotero_data.keys()
    skip = ['date', 'creators', 'itemType']
    fields_for_translation = [key for key in zotero_data.keys() if key not in skip and zotero_data[key]]
    for field in fields_for_translation:
        try:
            output[field_map['csl'][field]] = zotero_data[field]
        except KeyError:
            pass
    if 'creators' in zotero_fields:
        names = resolve_names(zotero_data, 'csl')
        for contrib_type in names.keys():
            output[contrib_type] = names[contrib_type]
    if 'date' in zotero_fields:
        output['issued'] = { 'raw' : zotero_data['date'] }
    return json.dumps(output)

def as_readable(zotero_json_string):
    zotero_data_list = []
    zotero_data = json.loads(zotero_json_string, object_pairs_hook=OrderedDict)
    for key, val in zotero_data.items():
        if key == 'itemType':
            readable_data = (key, type_map['readable'][val], 'Item Type')
        elif key == 'creators' and val:
            readable_data = resolve_names(zotero_data, 'readable')
        elif key == 'tags':
            continue
        elif val:
            readable_data = (key, val, field_map['readable'][key])
        else:
            readable_data = False
        if readable_data:
            if isinstance(readable_data, tuple):
                keys = ('zotero_key', 'value', 'label')
                zotero_data_list.append( dict(zip(keys, readable_data)) )
            elif isinstance(readable_data, list):
                zotero_data_list += readable_data
    return zotero_data_list

def get_creator_name(contributor):
    name_parts = [contributor[key] for key in contributor.keys()
                  if key != 'creatorType']
    name = contributor.get('lastName') or contributor.get('name') or ''
    name += ', %s' % contributor.get('firstName') if contributor.get('firstName') else ''
    return name or None

def resolve_names(zotero_data, format):
    if format == 'csl':
        # CSl output requires a dictionary whose keys are each creator type.
        # The values of these keys are lists containing individual dictionaries
        # containing the parts of each contributors' name. Example:
        #
        #{ 'author' : [{ "family" : "Doe", "given" : "Jane"},
        #              { "family" : "Doe", "given" : "John"}],
        #  'recipient' : [etc]}
        contribs = {}
        for creator in zotero_data['creators']:
            try:
                name = { "family" : creator['lastName'], "given" : creator['firstName'] }
            except:
                name = { "literal" : creator['name'] }
            try:
                contribs.setdefault(contrib_map['csl'][creator['creatorType']], []).append(name)
            except KeyError:
                pass

    if format == 'facets':
        # Data to be used in facets only needs a sortable name, either 'lastName' or 'name'
        contribs = []
        for creator in zotero_data['creators']:
            name = creator.get('lastName') or creator.get('name')
            contribs.append({creator['creatorType'] : name})
        
    if format == 'readable':
        contribs = []
        for creator in zotero_data['creators']:
            # This is needed because blank creators are kept inside the zotero
            # json, for easier inline editing. If a creator doesn't have a name,
            # that data isn't rendered.
            if not any([creator[key] for key in creator.keys()
                        if key != 'creatorType']):
                continue
            name = creator.get('name') or '%(firstName)s %(lastName)s' % creator
            contribs.append({'zotero_key' : creator['creatorType'],
                             'label' : contrib_map['readable'][creator['creatorType']],
                             'value' : name})
    return contribs

def parse_xml(url):
    try:
        zotero_url = ZOTERO_BASE_URL + url
        page = urlopen(zotero_url)
        xml_parse = etree.parse(page)
        page.close()
        root = xml_parse.getroot()
        return {'items' : root.xpath('./atom:entry', namespaces=NS),
                'count' : root.xpath('./zot:totalResults', namespaces=NS)[0].text}
    except HTTPError, error:
        error_content = error.read()
        raise Exception

# Map to translate JSON from Zotero to something understandable by citeproc-js CSL engine.
# See http://gsl-nagoya-u.net/http/pub/csl-fields/
field_map = {'csl': {'artworkSize': 'genre', 'letterType': 'genre', 'DOI': 'DOI', 'ISBN': 'ISBN', 'meetingName': 'event', 'extra': 'note', 'series': 'collection-title', 'history': 'references', 'codeVolume': 'volume', 'edition': 'edition', 'code': 'container-title', 'references': 'references', 'distributor': 'publisher', 'seriesNumber': 'collection-number', 'abstractNote': 'abstract', 'dateEnacted': 'issued', 'archive': 'archive', 'numberOfVolumes': 'number-of-volumes', 'caseName': 'title', 'episodeNumber': 'number', 'programTitle': 'container-title', 'rights': 'rights', 'court': 'authority', 'network': 'publisher', 'blogTitle': 'container-title', 'proceedingsTitle': 'container-title', 'section': 'section', 'label': 'publisher', 'accessDate': 'accessed', 'documentNumber': 'number', 'version': 'version', 'websiteType': 'genre', 'mapType': 'genre', 'postType': 'genre', 'presentationType': 'genre', 'dictionaryTitle': 'container-title', 'pages': 'page', 'subject': 'title', 'issue': 'issue', 'company': 'publisher', 'nameOfAct': 'title', 'seriesTitle': 'collection-title', 'thesisType': 'genre', 'conferenceName': 'event', 'institution': 'publisher', 'reporter': 'container-title', 'archiveLocation': 'archive_location', 'bookTitle': 'container-title', 'billNumber': 'number', 'firstPage': 'page', 'volume': 'volume', 'callNumber': 'call-number', 'reporterVolume': 'volume', 'studio': 'publisher', 'publicLawNumber': 'number', 'patentNumber': 'number', 'interviewMedium': 'medium', 'codePages': 'page', 'forumTitle': 'container-title', 'manuscriptType': 'genre', 'numPages': 'number-of-pages', 'publisher': 'publisher', 'videoRecordingFormat': 'medium', 'audioRecordingFormat': 'medium', 'language': 'language', 'reportNumber': 'number', 'url': 'URL', 'issueDate': 'issued', 'university': 'publisher', 'title': 'title', 'artworkMedium': 'medium', 'dateDecided': 'issued', 'audioFileType': 'medium', 'docketNumber': 'number', 'publicationTitle': 'container-title', 'place': 'publisher-place', 'reportType': 'genre', 'encyclopediaTitle': 'container-title', 'genre': 'genre', 'websiteTitle': 'container-title'}, 'readable': {'code': 'Code', 'seriesNumber': 'Series Number', 'caseName': 'Case Name', 'extra': 'Extra', 'seriesText': 'Series Text', 'number': 'Number', 'codeVolume': 'Code Volume', 'ISSN': 'ISSN', 'conferenceName': 'Conference Name', 'session': 'Session', 'references': 'References', 'committee': 'Committee', 'episodeNumber': 'Episode Number', 'itemType': 'Type', 'title': 'Title', 'system': 'System', 'dateEnacted': 'Date Enacted', 'source': 'Source', 'reportType': 'Report Type', 'dictionaryTitle': 'Dictionary Title', 'dateDecided': 'Date Decided', 'company': 'Company', 'nameOfAct': 'Name of Act', 'artworkSize': 'Artwork Size', 'medium': 'Medium', 'filingDate': 'Filing Date', 'archiveLocation': 'Loc. in Archive', 'bookTitle': 'Book Title', 'libraryCatalog': 'Library Catalog', 'codeNumber': 'Code Number', 'volume': 'Volume', 'reportNumber': 'Report Number', 'issuingAuthority': 'Issuing Authority', 'pages': 'Pages', 'date': 'Date', 'interviewMedium': 'Medium', 'institution': 'Institution', 'abstractNote': 'Abstract', 'audioRecordingFormat': 'Format', 'shortTitle': 'Short Title', 'assignee': 'Assignee', 'issueDate': 'Issue Date', 'notes': 'Notes', 'rights': 'Rights', 'dateModified': 'Modified', 'publicationTitle': 'Publication', 'encyclopediaTitle': 'Encyclopedia Title', 'university': 'University', 'websiteTitle': 'Website Title', 'letterType': 'Type', 'ISBN': 'ISBN', 'attachments': 'Attachments', 'series': 'Series', 'programmingLanguage': 'Language', 'DOI': 'DOI', 'related': 'Related', 'edition': 'Edition', 'websiteType': 'Website Type', 'archive': 'Archive', 'distributor': 'Distributor', 'legalStatus': 'Legal Status', 'numberOfVolumes': '# of Volumes', 'subject': 'Subject', 'patentNumber': 'Patent Number', 'billNumber': 'Bill Number', 'scale': 'Scale', 'court': 'Court', 'network': 'Network', 'blogTitle': 'Blog Title', 'applicationNumber': 'Application Number', 'proceedingsTitle': 'Proceedings Title', 'section': 'Section', 'tags': 'Tags', 'label': 'Label', 'documentNumber': 'Document Number', 'version': 'Version', 'legislativeBody': 'Legislative Body', 'mapType': 'Type', 'postType': 'Post Type', 'presentationType': 'Type', 'journalAbbreviation': 'Journal Abbr', 'videoRecordingFormat': 'Format', 'issue': 'Issue', 'manuscriptType': 'Type', 'docketNumber': 'Docket Number', 'seriesTitle': 'Series Title', 'thesisType': 'Type', 'dateAdded': 'Date Added', 'reporter': 'Reporter', 'accessDate': 'Accessed', 'programTitle': 'Program Title', 'firstPage': 'First Page', 'runningTime': 'Running Time', 'meetingName': 'Meeting Name', 'studio': 'Studio', 'publicLawNumber': 'Public Law Number', 'artworkMedium': 'Medium', 'codePages': 'Code Pages', 'forumTitle': 'Forum/Listserv Title', 'numPages': '# of Pages', 'publisher': 'Publisher', 'language': 'Language', 'callNumber': 'Call Number', 'url': 'URL', 'country': 'Country', 'audioFileType': 'File Type', 'reporterVolume': 'Reporter Volume', 'place': 'Place', 'priorityNumbers': 'Priority Numbers', 'history': 'History', 'genre': 'Genre'}}

type_map = {'csl' : {'document': 'article', 'manuscript': 'manuscript', 'radioBroadcast': 'broadcast', 'dictionaryEntry': 'chapter', 'hearing': 'bill', 'thesis': 'thesis', 'film': 'motion_picture', 'conferencePaper': 'paper-conference', 'journalArticle': 'article-journal', 'patent': 'patent', 'webpage': 'webpage', 'book': 'book', 'instantMessage': 'personal_communication', 'interview': 'interview', 'presentation': 'speech', 'email': 'personal_communication', 'forumPost': 'webpage', 'map': 'map', 'videoRecording': 'motion_picture', 'blogPost': 'webpage', 'newspaperArticle': 'article-newspaper', 'letter': 'personal_communication', 'artwork': 'graphic', 'report': 'report', 'podcast': 'song', 'audioRecording': 'song', 'case': 'legal_case', 'statute': 'bill', 'computerProgram': 'book', 'bill': 'bill', 'bookSection': 'chapter', 'tvBroadcast': 'broadcast', 'magazineArticle': 'article-magazine', 'encyclopediaArticle': 'chapter'}, 'readable' : {'forumPost': 'Forum Post', 'map': 'Map', 'instantMessage': 'Instant Message', 'videoRecording': 'Video Recording', 'thesis': 'Thesis', 'manuscript': 'Manuscript', 'radioBroadcast': 'Radio Broadcast', 'blogPost': 'Blog Post', 'dictionaryEntry': 'Dictionary Entry', 'hearing': 'Hearing', 'newspaperArticle': 'Newspaper Article', 'letter': 'Letter', 'artwork': 'Artwork', 'report': 'Report', 'podcast': 'Podcast', 'audioRecording': 'Audio Recording', 'film': 'Film', 'conferencePaper': 'Conference Paper', 'case': 'Case', 'statute': 'Statute', 'computerProgram': 'Computer Program', 'journalArticle': 'Journal Article', 'patent': 'Patent', 'bill': 'Bill', 'bookSection': 'Book Section', 'magazineArticle': 'Magazine Article', 'webpage': 'Webpage', 'book': 'Book', 'encyclopediaArticle': 'Encyclopedia Article', 'interview': 'Interview', 'document': 'Document', 'presentation': 'Presentation', 'email': 'Email', 'tvBroadcast': 'TV Broadcast'}}

# Not all creator types map to CSL in the zotero engine.
# For mappings, see these files in Zotero source:
# CSL: zotero/chrome/content/zotero/xpcom/utilities.js
# English: zotero/chrome/locale/en-US/zotero/zotero.properties
contrib_map = {'csl' : {'author': 'author', 'contributor' : 'author', 'bookAuthor': 'container-author', 'seriesEditor': 'collection-editor', 'translator': 'translator', 'editor': 'editor', 'interviewer': 'interviewer', 'recipient': 'recipient', 'interviewee' : 'contributor'}, 'readable' : {'artist': 'Artist', 'attorneyAgent': 'Attorney', 'author': 'Author', 'bookAuthor': 'Book', 'cartographer': 'Cartographer', 'castMember': 'Cast', 'commenter': 'Commenter', 'composer': 'Composer', 'contributor': 'Contributor', 'cosponsor': 'Cosponsor', 'counsel': 'Counsel', 'director': 'Director', 'editor': 'Editor', 'guest': 'Guest', 'interviewee': 'Interview', 'interviewer': 'Interviewer', 'inventor': 'Inventor', 'performer': 'Performer', 'podcaster': 'Podcaster', 'presenter': 'Presenter', 'producer': 'Producer', 'programmer': 'Programmer', 'recipient': 'Recipient', 'reviewedAuthor': 'Reviewed', 'scriptwriter': 'Scriptwriter', 'seriesEditor': 'Series', 'sponsor': 'Sponsor', 'translator': 'Translator', 'wordsBy': 'Words'}}

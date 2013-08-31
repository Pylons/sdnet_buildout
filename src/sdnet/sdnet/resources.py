import datetime

import colander
import deform.widget
import deform_bootstrap.widget
from persistent import Persistent
from sddci.interfaces import IFull
from sddci.interfaces import IMinimal
from sddci.schema import MinimalPropertySheet
from sddci.schema import FullPropertySheet
from sddci.schema import update_dci
from sddci.schema import _utc_now
from substanced.content import content
from substanced.file import File as File_
from substanced.file import FilePropertySheet as FPS
from substanced.file import FileUploadPropertySheet as FUPS
from substanced.folder import Folder as Folder_
from substanced.interfaces import IRoot
from substanced.property import PropertySheet
from substanced.root import Root as RootBase
from substanced.root import RootSchema as RootSchemaBase
from substanced.schema import Schema
from substanced.schema import NameSchemaNode
from substanced.util import find_content
from substanced.util import renamer
from zope.interface import implementer


class DCIPropertySheet(PropertySheet):

    def set(self, struct, omit=()):
        changed = super(DCIPropertySheet, self).set(struct, omit)
        if changed:
            update_dci(self.context, self.request, struct)
        return changed

#==============================================================================
# Folder resource (override to add DCI)
#==============================================================================
@content(
    'Folder',
    icon='icon-folder-close',
    add_view='add_folder',
    propertysheets = (
        ('DCI', MinimalPropertySheet),
        ),
    )
@implementer(IMinimal)
class Folder(Folder_):
    pass


#==============================================================================
# File resource (override to add DCI)
#==============================================================================
class FilePropertySheet(FPS):

    def set(self, struct, omit=()):
        changed = super(FilePropertySheet, self).set(struct, omit)
        if changed:
            update_dci(self.context, self.request, struct)
        return changed


class FileUploadPropertySheet(FUPS):

    def set(self, struct):
        super(FileUploadPropertySheet, self).set(struct)
        update_dci(self.context, self.request, struct)
        return True


@content(
    'File',
    icon='icon-file',
    add_view='add_file',
    tab_order = ('properties', 'acl_edit', 'view'),
    propertysheets = (
        ('Basic', FilePropertySheet),
        ('Upload', FileUploadPropertySheet),
        ('DCI', MinimalPropertySheet),
        ),
    catalog = True,
    )
@implementer(IMinimal)
class File(File_):
    pass


#==============================================================================
# Document resource
#==============================================================================
def context_is_a_document(context, request):
    return request.registry.content.istype(context, 'Document')

def _update_modified_modifier(context, request):
    context.modified = datetime.datetime.utcnow()
    context.modifier = request.user.__name__


class DocumentSchema(Schema):
    name = NameSchemaNode(
        editing=context_is_a_document,
        )
    title = colander.SchemaNode(
        colander.String(),
        )
    body = colander.SchemaNode(
        colander.String(),
        missing='',
        widget = deform.widget.TextAreaWidget(rows=20, cols=70),
        )
    body_format = colander.SchemaNode(
        colander.String(),
        validator = colander.OneOf(['rst', 'html']),
        widget = deform.widget.SelectWidget(
            values=[('rst', 'rst'), ('html', 'html')]),
        )


class DocumentPropertySheet(DCIPropertySheet):
    schema = DocumentSchema()


@content(
    'Document',
    icon='icon-align-left',
    add_view='add_document',
    propertysheets = (
            ('Basic', DocumentPropertySheet),
            ('DCI', FullPropertySheet),
        ),
    )
@implementer(IFull)
class Document(Persistent):

    name = renamer()
    body = ''
    body_format = 'rst'

    def __init__(self, title='', body='', body_format=''):
        self.title = title
        self.body = body
        self.body_format = body_format

#==============================================================================
# Timeline resources
#==============================================================================

class TimelineEventSchema(Schema):
    name = NameSchemaNode(
        editing=lambda c, r: r.registry.content.istype(c, 'Timeline Event')
        )
    title = colander.SchemaNode(
        colander.String(),
        )
    description = colander.SchemaNode(
        colander.String(),
        widget = deform.widget.TextAreaWidget(rows=20, cols=70),
        )
    format = colander.SchemaNode(
        colander.String(),
        validator = colander.OneOf(['rst', 'html']),
        widget = deform.widget.SelectWidget(
            values=[('rst', 'rst'), ('html', 'html')]),
        )
    date = colander.SchemaNode(
       colander.DateTime(),
       )


class TimelineEventPropertySheet(DCIPropertySheet):
    schema = TimelineEventSchema()


@content(
    'Timeline Event',
    icon='icon-calendar',
    add_view='add_timeline_event',
    propertysheets=(
            ('Basic', TimelineEventPropertySheet),
            ('DCI', MinimalPropertySheet),
        ),
    tab_order=('properties', 'contents', 'acl_edit'),
    )
@implementer(IMinimal)
class TimelineEvent(Persistent):

    name = renamer()

    def __init__(self, title, description, format, date):
        self.modified = datetime.datetime.utcnow()
        self.title = title
        self.description = description
        self.date = date
        self.format = format


class TimelineSchema(Schema):
    """ The schema representing the blog root. """
    name = NameSchemaNode(
        editing=lambda c, r: r.registry.content.istype(c, 'Blog')
        )
    title = colander.SchemaNode(
        colander.String(),
        missing=''
        )
    description = colander.SchemaNode(
        colander.String(),
        missing=''
        )


class TimelinePropertySheet(DCIPropertySheet):
    schema = TimelineSchema()


@content(
    'Timeline',
    icon='icon-calendar',
    add_view='add_timeline',
    propertysheets = (
            ('Basic', TimelinePropertySheet),
            ('DCI', MinimalPropertySheet),
        ),
    )
@implementer(IMinimal)
class Timeline(Folder):
    name = renamer()
    title = ''
    description = ''

    def __init__(self, title, description=''):
        super(Timeline, self).__init__()
        self.title = title
        self.description = description

    @property
    def sdi_title(self):
        return self.title

    @sdi_title.setter
    def sdi_title(self, value):
        self.title = value

#==============================================================================
# Blog resources
#==============================================================================

@colander.deferred
def now_default(node, kw):
    return _utc_now()


class CategoriesSchemaNode(colander.SchemaNode):
    """ A SchemaNode which represents a set of categories /keywords.

    Uses a widget which queries the parent for allowed values.
    """
    def schema_type(self):
        return deform.Set(allow_empty=True)

    @property
    def _choices(self):
        context = self.bindings['context']
        return find_content(context, 'Blog').categories

    @property
    def widget(self):
        choices = [(x, x) for x in self._choices]
        return deform_bootstrap.widget.ChosenMultipleWidget(values=choices)
    def validator(self, node, value):
        allowed = self._choices
        for category in value:
            if not category in allowed:
                raise colander.Invalid(
                    node, 'Unknown category %s' % value, value
                    )


class BlogEntrySchema(Schema):
    name = NameSchemaNode(
        editing=lambda c, r: r.registry.content.istype(c, 'Blog Entry')
        )
    title = colander.SchemaNode(
        colander.String(),
        )
    categories = CategoriesSchemaNode()
    entry = colander.SchemaNode(
        colander.String(),
        widget = deform.widget.TextAreaWidget(rows=20, cols=70),
        )
    format = colander.SchemaNode(
        colander.String(),
        validator = colander.OneOf(['rst', 'html']),
        widget = deform.widget.SelectWidget(
            values=[('rst', 'rst'), ('html', 'html')]),
        )
    pubdate = colander.SchemaNode(
       colander.DateTime(),
       default = now_default,
       )


class BlogEntryPropertySheet(DCIPropertySheet):
    schema = BlogEntrySchema()


@content(
    'Blog Entry',
    icon='icon-book',
    add_view='add_blog_entry',
    propertysheets=(
            ('Basic', BlogEntryPropertySheet),
            ('DCI', MinimalPropertySheet),
        ),
    tab_order=('properties', 'contents', 'acl_edit'),
    )
@implementer(IMinimal)
class BlogEntry(Folder):

    name = renamer()

    def __init__(self, title, categories, entry, format, pubdate):
        Folder.__init__(self)
        self.modified = datetime.datetime.utcnow()
        self.title = title
        self.categories = categories
        self.entry = entry
        self.pubdate = pubdate
        self.format = format
        self['attachments'] = Folder()


class BlogSchema(Schema):
    """ The schema representing the blog root. """
    name = NameSchemaNode(
        editing=lambda c, r: r.registry.content.istype(c, 'Blog')
        )
    title = colander.SchemaNode(
        colander.String(),
        missing=''
        )
    description = colander.SchemaNode(
        colander.String(),
        missing=''
        )
    categories = colander.SchemaNode(
        colander.Sequence(),
        colander.SchemaNode(colander.String(), name='category'),
        missing=(),
        )


class BlogPropertySheet(DCIPropertySheet):
    schema = BlogSchema()


@content(
    'Blog',
    icon='icon-home',
    add_view='add_blog',
    propertysheets = (
            ('Basic', BlogPropertySheet),
            ('DCI', MinimalPropertySheet),
        ),
    )
@implementer(IMinimal)
class Blog(Folder):
    name = renamer()
    title = ''
    description = ''
    categories = ()

    def __init__(self, title, description='', categories=()):
        super(Blog, self).__init__()
        self.title = title
        self.description = description
        self.categories = categories

    @property
    def sdi_title(self):
        return self.title

    @sdi_title.setter
    def sdi_title(self, value):
        self.title = value


class NavLinkSchema(Schema):
    title = colander.SchemaNode(
        colander.String(),
        )
    relative_url = colander.SchemaNode(
        colander.String(),
        )


class RootSchema(RootSchemaBase):
    """ The schema representing site properties. """
    prolog = colander.SchemaNode(
        colander.String(),
        missing='',
        widget = deform.widget.TextAreaWidget(rows=10, cols=70),
        )
    prolog_format = colander.SchemaNode(
        colander.String(),
        validator = colander.OneOf(['rst', 'html']),
        widget = deform.widget.SelectWidget(
            values=[('rst', 'rst'), ('html', 'html')]),
        )
    nav_links = colander.SchemaNode(
        colander.Sequence(),
        NavLinkSchema()
        )


class RootPropertySheet(DCIPropertySheet):
    schema = RootSchema()


@content(
    'Root',
    icon='icon-home',
    propertysheets = (
            ('Basic', RootPropertySheet),
            ('DCI', MinimalPropertySheet),
        ),
    after_create='after_create',
    )
@implementer(IRoot, IMinimal)
class Root(RootBase):
    prolog_format = 'rst'
    prolog = '**Replace me**'
    nav_links = ()

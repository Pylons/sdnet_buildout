import datetime
import colander
import deform.widget
from persistent import Persistent
from substanced.content import content
from substanced.file import File as File_
from substanced.file import FilePropertySheet
from substanced.file import FileUploadPropertySheet
from substanced.folder import Folder as Folder_
from substanced.interfaces import IRoot
from substanced.property import PropertySheet
from substanced.root import Root as RootBase
from substanced.root import RootSchema as RootSchemaBase
from substanced.schema import Schema
from substanced.schema import NameSchemaNode
from substanced.util import renamer
from zope.interface import implementer

#==============================================================================
# Folder resource (overrideable content decorator)
#==============================================================================
@content(
    'Folder',
    icon='icon-folder-close',
    add_view='add_folder',
    )
class Folder(Folder_):
    pass


@content(
    'File',
    icon='icon-file',
    add_view='add_file',
    tab_order = ('properties', 'acl_edit', 'view'),
    propertysheets = (
        ('Basic', FilePropertySheet),
        ('Upload', FileUploadPropertySheet),
        ),
    catalog = True,
    )
class File(File_):
    pass


#==============================================================================
# Document resource
#==============================================================================
def context_is_a_document(context, request):
    return request.registry.content.istype(context, 'Document')

@colander.deferred
def today(node, kw):
    return datetime.datetime.today()

@colander.deferred
def current_username(node, kw):
    return kw['request'].user.__name__

class DocumentSchema(Schema):
    name = NameSchemaNode(
        editing=context_is_a_document,
        )
    title = colander.SchemaNode(
        colander.String(),
        )
    icon = colander.SchemaNode(
        colander.String(),
        missing='',
        )
    image = colander.SchemaNode(
        colander.String(),
        missing='',
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
    created = colander.SchemaNode(
        colander.Date(),
        default=today,
        )
    modified = colander.SchemaNode(
        colander.Date(),
        default=today,
        )
    creator = colander.SchemaNode(
        colander.String(),
        default=current_username,
        )

class DocumentPropertySheet(PropertySheet):
    schema = DocumentSchema()


@content(
    'Document',
    icon='icon-align-left',
    add_view='add_document',
    propertysheets = (
            ('Basic', DocumentPropertySheet),
        ),
    )
class Document(Persistent):

    name = renamer()
    body = ''
    body_format = 'rst'
    icon = ''
    image = ''

    def __init__(
        self,
        title='',
        body='',
        body_format='',
        icon='',
        image='',
        created=None,
        modified=None,
        creator=''
        ):
        self.title = title
        self.body = body
        self.body_format = body_format
        self.icon = icon
        self.image = image
        if created is None:
            created = datetime.datetime.today()
        if modified is None:
            modified = datetime.datetime.today()
        self.created = created
        self.modified = modified
        self.creator = creator

class RootSchema(RootSchemaBase):
    """ The schema representing site properties. """
    pass


class RootPropertySheet(PropertySheet):
    schema = RootSchema()

@content(
    'Root',
    icon='icon-home',
    propertysheets = (
            ('Basic', RootPropertySheet),
        ),
    after_create='after_create',
    )
@implementer(IRoot)
class Root(RootBase):
    pass

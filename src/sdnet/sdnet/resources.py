import datetime

import colander
import deform.widget
from persistent import Persistent
from sddci.interfaces import IFull
from sddci.interfaces import IMinimal
from sddci.schema import MinimalPropertySheet
from sddci.schema import FullPropertySheet
from sddci.schema import update_dci
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

class RootSchema(RootSchemaBase):
    """ The schema representing site properties. """
    pass


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
    pass

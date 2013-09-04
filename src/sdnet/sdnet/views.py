from docutils.core import publish_parts
from webob import Response

from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import get_renderer
from pyramid.view import view_config
from substanced.sdi import mgmt_view
from substanced.file.views import AddFileView as AddFileView_
from substanced.folder.views import AddFolderView as AddFolderView_
from substanced.form import FormView
from substanced.interfaces import IFolder

from .resources import Document
from .resources import DocumentSchema

def _namespace(context, **kw):
    ns = {'master': get_renderer('templates/master.pt').implementation(),
         }
    ns.update(kw)
    return ns

def _cook(format, entry):
    if format == 'rst':
       body = publish_parts(entry, writer_name='html')['fragment']
    else:
       body = entry
    return body

#==============================================================================
#   Default "retail" view
#==============================================================================
@view_config(
    renderer='templates/splash.pt',
    )
def splash_view(context, request):
    return _namespace(context)

#==============================================================================
#   "Retail" view for documents.
#==============================================================================
@view_config(
    context=Document,
    renderer='templates/document.pt',
    )
def document_view(context, request):
    body = _cook(context.body_format, context.body)
    return _namespace(
        context,
        title=context.title,
        body=body,
    )

@view_config(
    content_type='File',
    name='download.html',
    )
def download_attachment(context, request):
    f = context.blob.open()
    headers = [('Content-Type', str(context.mimetype)),
               ('Content-Disposition',
                    'attachment;filename=%s' % str(context.__name__)),
              ]
    response = Response(headerlist=headers, app_iter=f)
    return response


#==============================================================================
#   Override stock SDI "add" view for folders
#==============================================================================
@mgmt_view(
    context=IFolder,
    name='add_folder',
    tab_title='Add Folder',
    tab_condition=False,
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt'
    )
class AddFolderView(AddFolderView_):

    def add_success(self, appstruct):
        request = self.request
        registry = request.registry
        name = appstruct['name']
        folder = registry.content.create('Folder')
        self.context[name] = folder
        return HTTPFound(location=self.request.sdiapi.mgmt_path(self.context))


#==============================================================================
#   Override stock SDI "add" view for files
#==============================================================================
@mgmt_view(
    context=IFolder,
    name='add_file',
    tab_condition=False,
    tab_title='Add File',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt'
    )
class AddFileView(AddFileView_):

    def add_success(self, appstruct):
        name = appstruct['name']
        super(AddFileView, self).add_success(appstruct)
        file = self.context[name]
        return HTTPFound(self.request.sdiapi.mgmt_path(file, '@@properties'))


#==============================================================================
#   SDI "add" view for documents
#==============================================================================

@mgmt_view(
    context=IFolder,
    name='add_document',
    tab_title='Add Document',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt',
    tab_condition=False,
    )
class AddDocumentView(FormView):
    title = 'Add Document'
    schema = DocumentSchema()
    buttons = ('add',)

    def add_success(self, appstruct):
        request = self.request
        registry = request.registry
        name = appstruct.pop('name')
        document = registry.content.create('Document', **appstruct)
        self.context[name] = document
        return HTTPFound(
            self.request.sdiapi.mgmt_path(self.context, '@@contents')
            )


import datetime
import pytz

from docutils.core import publish_parts
from webob import Response

from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import get_renderer
from pyramid.security import authenticated_userid
from pyramid.traversal import find_root
from pyramid.traversal import resource_path
from pyramid.url import resource_url
from pyramid.view import view_config
from sddci.schema import update_dci
from substanced.sdi import mgmt_view
from substanced.sdi.views.file import AddFileView as AddFileView_
from substanced.sdi.views.folder import AddFolderView as AddFolderView_
from substanced.form import FormView
from substanced.interfaces import IFolder
from substanced.objectmap import find_objectmap
from substanced.util import find_catalog

from .resources import Document
from .resources import DocumentSchema
from .resources import BlogSchema
from .resources import BlogEntrySchema
from .resources import TimelineSchema
from .resources import TimelineEventSchema

def _namespace(context, **kw):
    root = find_root(context)
    ns = {'master': get_renderer('templates/master_venera.pt').implementation(),
          'nav_links': root.nav_links,
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
    sys_catalog = find_catalog(request.context, 'system')
    blog_catalog = find_catalog(request.context, 'blog')

    ctype = sys_catalog['content_type']
    allowed = sys_catalog['allowed']
    pubdate = blog_catalog['pubdate']

    q = (ctype.eq('Blog Entry') & allowed.allows(request, 'view') )

    resultset = q.execute().sort(pubdate, limit=5, reverse=True)
    entries = []
    for entry in list(resultset):
        entries.append({
            'title': entry.title,
            'url': resource_url(entry, request),
            'pubdate': entry.pubdate,
        })
    prolog = _cook(context.prolog_format, context.prolog)
    return _namespace(
        context,
        prolog=prolog,
        entries=entries,
    )

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

#==============================================================================
# Timeline retail view
#==============================================================================
@view_config(
    renderer='templates/timeline.pt',
    content_type='Timeline',
    )
def timeline_view(context, request):
    content = request.registry.content
    events = [{'title': event.title,
               'description': _cook(event.format, event.description),
               'date': event.date.date().isoformat(),
              } for event in context.values()
                    if content.istype(event, 'Timeline Event')]
    logged_in = authenticated_userid(request)
    return _namespace(
        context,
        request = request,
        logged_in = logged_in,
        events = sorted(events, key=lambda x: x['date']),
        timeline_url = request.resource_url(context),
        title = context.title,
        )


#==============================================================================
# Blog retail views
#==============================================================================

def _add_updated_strings(updated, info):
    if getattr(updated, 'now', None) is None:
        y, mo, d, h, mi, s = updated.timetuple()[:6]
        updated = datetime.datetime(y, mo, d, h, mi, s, tzinfo=pytz.utc)
    info['updated_atom'] = updated.astimezone(pytz.utc).isoformat()
    info['updated_rss'] = updated.strftime('%a, %d %b %Y %H:%M:%S %z')

def _nowtz():
    now = datetime.datetime.utcnow() # naive
    y, mo, d, h, mi, s = now.timetuple()[:6]
    return datetime.datetime(y, mo, d, h, mi, s, tzinfo=pytz.utc)

def _get_feed_info(context, request):
    start = int(request.GET.get('start', 0))
    batchsize = int(request.GET.get('batchsize', 15))
    category = request.GET.get('category')
    sys_catalog = find_catalog(context, 'system')
    blog_catalog = find_catalog(context, 'blog')
    objectmap = find_objectmap(context)
    resolve = objectmap.object_for

    ctype = sys_catalog['content_type']
    allowed = sys_catalog['allowed']
    path = sys_catalog['path']
    pubdate = blog_catalog['pubdate']
    categories = blog_catalog['categories']

    q = (ctype.eq('Blog Entry') &
         allowed.allows(request, 'view') &
         path.eq(resource_path(context))
        )

    if category is not None:
        q &= categories.eq(category)

    resultset = q.execute().sort(pubdate, reverse=True).all(resolve=False)
    feed = {"rss_url": request.resource_url(context, 'rss.xml'),
            "atom_url": request.resource_url(context, 'index.atom'),
            "blog_url": request.resource_url(context),
            "title": context.sdi_title,
            "description": context.description,
           }

    blogentries = []
    for oid in list(resultset)[start:start+batchsize]:
        blogentry = resolve(oid)
        name = blogentry.__name__
        updated = blogentry.pubdate
        info = {'url': resource_url(blogentry, request),
                'title': blogentry.title,
                'body': _cook(blogentry.format, blogentry.entry),
                'created': updated,
                'pubdate': updated,
                'author': blogentry.creator,
                }
        _add_updated_strings(updated, info)
        blogentries.append(info)

    updated = blogentries and blogentries[0]['pubdate'] or _nowtz()
    _add_updated_strings(updated, feed)

    return feed, blogentries

@view_config(
    renderer='templates/blog.pt',
    content_type='Blog',
    )
def blogview(context, request):
    feed, blogentries = _get_feed_info(context, request)
    logged_in = authenticated_userid(request)
    category = request.GET.get('category')
    kw = {}
    if category is not None:
        kw['query'] = {'category': category}
    rss_url = request.resource_url(context, 'rss.xml', **kw)
    atom_url = request.resource_url(context, 'index.atom', **kw)
    return _namespace(
        context,
        request = request,
        logged_in = logged_in,
        blogentries = reversed(sorted(blogentries, key=lambda x: x['pubdate'])),
        rss_url = rss_url,
        atom_url = atom_url,
        blog_url = request.resource_url(context),
        title = context.title,
        categories = context.categories,
        category = category,
        )

@view_config(
    content_type='Blog Entry',
    renderer='templates/blogentry.pt',
    )
def blogentry_view(context, request):
    attachments = context['attachments'].values()

    body = _cook(context.format, context.entry)
    logged_in = authenticated_userid(request)
    blog = context.__parent__
    return _namespace(
        context,
        blogentry = body,
        request = request,
        title = context.title,
        entry = context.entry,
        format = context.format,
        pubdate = context.pubdate,
        url = request.resource_url(context),
        attachments = attachments,
        logged_in = logged_in,
        blog_url = request.resource_url(context.__parent__),
        author = context.creator,
        rss_url = request.resource_url(blog, 'rss.xml'),
        atom_url = request.resource_url(blog, 'index.atom'),
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


class FeedViews(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(
        name='rss.xml',
        renderer='templates/rss.pt',
        )
    def blog_rss(self):
        feed, blogentries = _get_feed_info(self.context, self.request)
        self.request.response.content_type = 'application/rss+xml'
        return dict(
            feed = feed,
            blogentries = blogentries,
            )

    @view_config(
        name='index.atom',
        renderer='templates/atom.pt',
        )
    def blog_atom(self):
        feed, blogentries = _get_feed_info(self.context, self.request)
        self.request.response.content_type = 'application/atom+xml'
        return dict(
            feed = feed,
            blogentries = blogentries,
            )


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
        update_dci(folder, request, appstruct)
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
        request = self.request
        name = appstruct['name']
        super(AddFileView, self).add_success(appstruct)
        file = self.context[name]
        update_dci(file, request, appstruct)
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
        update_dci(document, request, appstruct)
        self.context[name] = document
        return HTTPFound(
            self.request.sdiapi.mgmt_path(self.context, '@@contents')
            )

#==============================================================================
#   SDI "add" view for timelines
#==============================================================================

@mgmt_view(
    context=IFolder,
    name='add_timeline',
    tab_title='Add Timeline',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt',
    tab_condition=False,
    )
class AddTimelineView(FormView):
    title = 'Add Timeline'
    schema = TimelineSchema()
    buttons = ('add',)

    def add_success(self, appstruct):
        name = appstruct.pop('name')
        request = self.request
        timeline = request.registry.content.create('Timeline', **appstruct)
        update_dci(timeline, request, appstruct)
        self.context[name] = timeline
        loc = request.mgmt_path(self.context, name, '@@properties')
        return HTTPFound(location=loc)


#==============================================================================
#   SDI "add" view for timeline events
#==============================================================================

@mgmt_view(
    content_type='Timeline',
    name='add_timeline_event',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt',
    tab_condition=False,
    )
class AddTimelineEventView(FormView):
    title = 'Add Timeline Event'
    schema = TimelineEventSchema()
    buttons = ('add',)

    def add_success(self, appstruct):
        name = appstruct.pop('name')
        request = self.request
        event = request.registry.content.create('Timeline Event', **appstruct)
        update_dci(event, request, appstruct)
        self.context[name] = event
        loc = request.mgmt_path(self.context, name, '@@properties')
        return HTTPFound(location=loc)


#==============================================================================
#   SDI "add" view for blogs
#==============================================================================

@mgmt_view(
    context=IFolder,
    name='add_blog',
    tab_title='Add Blog',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt',
    tab_condition=False,
    )
class AddBlogView(FormView):
    title = 'Add Blog'
    schema = BlogSchema()
    buttons = ('add',)

    def add_success(self, appstruct):
        name = appstruct.pop('name')
        request = self.request
        blog = request.registry.content.create('Blog', **appstruct)
        update_dci(blog, request, appstruct)
        self.context[name] = blog
        loc = request.mgmt_path(self.context, name, '@@properties')
        return HTTPFound(location=loc)


#==============================================================================
#   SDI "add" view for blog entries
#==============================================================================

@mgmt_view(
    content_type='Blog',
    name='add_blog_entry',
    permission='sdi.add-content',
    renderer='substanced.sdi:templates/form.pt',
    tab_condition=False,
    )
class AddBlogEntryView(FormView):
    title = 'Add Blog Entry'
    schema = BlogEntrySchema()
    buttons = ('add',)

    def add_success(self, appstruct):
        name = appstruct.pop('name')
        request = self.request
        blogentry = request.registry.content.create('Blog Entry', **appstruct)
        update_dci(blogentry, request, appstruct)
        self.context[name] = blogentry
        loc = request.mgmt_path(self.context, name, '@@properties')
        return HTTPFound(location=loc)

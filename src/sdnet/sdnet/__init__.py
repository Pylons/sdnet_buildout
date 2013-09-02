from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.config import Configurator
from pyramid_multiauth import MultiAuthenticationPolicy
from substanced import root_factory
from substanced.catalog import catalog_factory
from substanced.catalog import Field
from substanced.catalog import Keyword
from substanced.event import subscribe_created
from substanced.interfaces import MODE_ATCOMMIT
from substanced.principal import groupfinder
from substanced.util import find_service
from substanced.workflow import pub_workflow
from sddav.authentication import SDIBasicAuthPolicy

from .resources import Root


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory=root_factory)
    config.include('substanced')
    config.include('sddci.catalog')
    config.include('sddci.adapters')
    config.include('sddci.utilities')
    config.include('sddav')
    config.include('sdexternaledit')
    config.add_permission('view')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('assets', 'static/theme', cache_max_age=3600)
    config.add_indexview(get_pubdate,
                         catalog_name='blog', index_name='pubdate')
    config.add_indexview(get_categories,
                         catalog_name='blog', index_name='categories')
    config.add_workflow(pub_workflow, ('Blog Entry', 'Document'))
    secret = settings['substanced.secret']
    # NB: we use the AuthTktAuthenticationPolicy rather than the session
    # authentication policy because using the session policy can cause static
    # resources to be uncacheable.  In particular, if you use the
    # UnencryptedBlahBlahBlah session factory, and anything asks for the
    # authenticated or unauthenticated user from the policy, the session needs
    # to be reserialized because that factory works by resetting the cookie on
    # every access to set the last-accessed value.  In practice, pyramid_tm
    # asks for the unauthenticated user, so every static resource will have a
    # set-cookie header in it, making them uncacheable.  This could also be
    # solved by using a different session factory (e.g. pyramid_redis_sessions)
    # which does not reserialize the cookie on every access.
    authn_policy = MultiAuthenticationPolicy([
        AuthTktAuthenticationPolicy(secret, callback=groupfinder),
        SDIBasicAuthPolicy(),
    ])
    config.set_authentication_policy(authn_policy)
    config.scan()
    return config.make_wsgi_app()

def get_pubdate(resource, default):
    return getattr(resource, 'pubdate', default)

def get_categories(resource, default):
    return getattr(resource, 'categories', default)


@catalog_factory('blog')
class BlogCatalogFactory(object):
    pubdate = Field(action_mode=MODE_ATCOMMIT)
    categories = Keyword(action_mode=MODE_ATCOMMIT)


@subscribe_created(Root)
def root_created(event):
    root = event.object
    catalogs = find_service(root, 'catalogs')
    catalogs.add_catalog('blog', update_indexes=True)
    catalogs.add_catalog('dcterms', update_indexes=True)

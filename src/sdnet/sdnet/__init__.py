from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.config import Configurator
from substanced import root_factory
from substanced.principal import groupfinder

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings, root_factory=root_factory)
    config.include('substanced')
    config.include('sdexternaledit')
    config.add_permission('view')
    config.add_static_view('static', 'static', cache_max_age=86400)
    config.add_static_view('assets', 'static/theme', cache_max_age=86400)
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
    authn_policy = AuthTktAuthenticationPolicy(secret, callback=groupfinder)
    config.set_authentication_policy(authn_policy)
    config.scan()
    return config.make_wsgi_app()


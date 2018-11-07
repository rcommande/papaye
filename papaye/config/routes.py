from papaye.factories.root import (
    user_root_factory,
    application_factory,
    repository_root_factory,
)


def includeme(config):
    config.add_route('login', '/login/', factory=user_root_factory)
    config.add_route('logout', '/logout/')
    # config.add_route('api', '/api/v1/', factory=user_root_factory)
    config.add_route('packages', '/api/compat/package/json', factory=repository_root_factory)
    # config.add_route('package', '/api/compat/package/{package_name}/json', repository_root_factory)
    # config.add_route('package_version', '/api/compat/package/{package_name}/{version}/json', repository_root_factory)
    # config.add_route('package_version_filename', '/api/compat/package/{package_name}/{version}/{filename}/json', repository_root_factory)
    config.add_route(
        'simple',
        '/simple*traverse',
        factory='papaye.factories.root:repository_root_factory',
    )

    config.add_static_view('static', 'papaye:static', cache_max_age=3600)
    config.add_route('ssr', '/*path', factory=application_factory)
    # config.add_route('home', '/', factory=application_factory)

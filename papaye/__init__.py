from colander import Invalid
from pyramid.config import Configurator, ConfigurationError
from pyramid.interfaces import ISettings
from pyramid_beaker import set_cache_regions_from_settings
from zope.component import getGlobalSiteManager

from papaye.config.utils import SettingsReader

from papaye.config.schemas.settings import Settings


def deserialize(settings):
    try:
        settings_to_deserialize = {
            'papaye': {
                key.split('.')[-1]: value
                for key, value in settings.items()
                if key.startswith('papaye.')
            }
        }
        return Settings().deserialize(settings_to_deserialize)
    except Invalid:
        raise ConfigurationError('Settings error')


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    globalreg = getGlobalSiteManager()
    set_cache_regions_from_settings(settings)
    deserialized_settings = deserialize(settings)

    config = Configurator(registry=globalreg)
    config.setup_registry(settings=settings)

    config.registry.registerUtility(
        deserialized_settings,
        ISettings,
        name='settings'
    )
    config.add_directive('settings_reader', lambda c: SettingsReader(c))
    config.reader = SettingsReader(config)
    config.include('papaye.config.auth')
    config.include('papaye.config.routes')
    config.include('papaye.config.views')
    config.include('papaye.config.startup')
    config.add_renderer(
        name='json_api_compat',
        factory='papaye.views.api.compat.renderers.CompatAPIRendererFactory'
    )
    config.add_request_method(lambda x: {'truc': 'chose'}, name='state', property=True)
    config.commit()
    config.add_tween('papaye.tweens.LoginRequiredTweenFactory')
    config.add_tween('papaye.tweens.TestTweenFactory')
    config.scan(ignore=['papaye.tests', 'papaye.conftest'])
    config.add_request_method(
        lambda x: deserialized_settings,
        'papaye_settings',
        reify=True,
        property=True,
    )
    config.add_request_method(
        lambda x: {},
        'state',
        reify=True,
        property=True,
    )

    # def get_batch_url():
    #     return 'http://localhost:3030/batch'

    # config.registry.settings['pyramid_hypernova.get_batch_url'] = get_batch_url
    # config.add_tween('pyramid_hypernova.tweens.hypernova_tween_factory')

    # config.set_request_factory('papaye.factories.root.request_factory')
    return config.make_wsgi_app()

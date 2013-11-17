import shutil
import tempfile
import transaction
import types
import unittest

from os import mkdir
from os.path import join
from pyramid import testing
from pyramid.response import FileResponse
from pyramid.threadlocal import get_current_request, get_current_registry

from .models import DBSession
from papaye.views import SimpleView


class FakeMatchedDict(object):

    def __init__(self, name):
        self.name = name


class SimpleTestView(unittest.TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request=request)
        self.repository = tempfile.mkdtemp('repository')
        registry = get_current_registry()
        registry.settings = {'papaye.repository': self.repository}
        self.config.add_route('simple', 'simple/', static=True)
        mkdir(join(self.repository, 'package2'))
        mkdir(join(self.repository, 'package1'))
        open(join(self.repository, 'package1', 'file1.tar.gz'), 'w').close()
        open(join(self.repository, 'package1', 'file2.data'), 'w').close() # a bad file

    def tearDown(self):
        shutil.rmtree(self.repository)

    def test_list_packages(self):
        request = get_current_request()
        view = SimpleView(request)
        response = view.list_packages()
        self.assertIsInstance(response, types.GeneratorType)
        self.assertEqual([p for p in response],
                         [('package1', '/simple/package1'),
                          ('package2', '/simple/package2')])

    def test_list_releases(self):
        request = get_current_request()
        request.matchdict['package'] = 'package1'
        view = SimpleView(request)
        response = view.list_releases()
        self.assertIsInstance(response, tuple)
        self.assertTrue(len(response) == 2)
        self.assertIsInstance(response[0], types.GeneratorType)
        self.assertEqual([p for p in response[0]],
                         [('file1.tar.gz', '/simple/package1/file1.tar.gz', )])
        self.assertEqual(response[1], 'package1')

    def test_download_release(self):
        request = get_current_request()
        request.matchdict['package'] = 'package1'
        request.matchdict['release'] = 'file1.tar.gz'
        view = SimpleView(request)
        response = view.download_release()
        self.assertIsInstance(response, FileResponse)

    def test__call__with_simple_route(self):
        request = get_current_request()
        request.matched_route = FakeMatchedDict('simple')
        view = SimpleView(request)
        result = view()
        self.assertIsInstance(result, dict)
        self.assertIn('objects', result)

    def test__call__with_simple_release_route(self):
        request = get_current_request()
        request.matched_route = FakeMatchedDict('simple_release')
        request.matchdict['package'] = 'package1'
        view = SimpleView(request)
        result = view()
        self.assertIsInstance(result, dict)
        self.assertIn('objects', result)
        self.assertIn('package', result)
        self.assertEqual(result['package'], 'package1')

    def test__call_with_download_release_route(self):
        request = get_current_request()
        request.matched_route = FakeMatchedDict('download_release')
        request.matchdict['package'] = 'package1'
        request.matchdict['release'] = 'file1.tar.gz'
        view = SimpleView(request)
        result = view()
        self.assertIsInstance(result, FileResponse)


class TestMyView(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            MyModel,
        )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        with transaction.manager:
            model = MyModel(name='one', value=55)
            DBSession.add(model)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_it(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info['one'].name, 'one')
        self.assertEqual(info['project'], 'papaye')

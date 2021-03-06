import types
import unittest

from mock import patch
from pyramid import testing
from pyramid.response import Response
from pyramid.threadlocal import get_current_request

from papaye.tests.tools import (
    FakeGRequestResponse,
    FakeRoute,
    disable_cache,
    remove_blob_dir,
    set_database_connection,
    get_resource,
)

from papaye.factories import models as factories


class TestRoot(unittest.TestCase):

    def test_iter(self):
        package = factories.PackageFactory()
        root = package.__parent__

        result = iter(root)

        assert isinstance(result, types.GeneratorType)
        assert list(result) == [package, ]

    def test_get_index(self):
        package = factories.PackageFactory()
        root = package.__parent__

        result = root[0]

        assert result == package


class PackageTest(unittest.TestCase):

    def setUp(self):
        self.request = testing.DummyRequest(matched_route=FakeRoute('simple'))
        self.root = factories.RootFactory()
        self.request.root = self.root
        self.blob_dir = set_database_connection(self.request)
        settings = disable_cache()
        self.config = testing.setUp(request=self.request, settings=settings)

    def tearDown(self):
        remove_blob_dir(self.blob_dir)

    @patch('requests.get')
    def test_get_last_remote_version_without_proxy(self, mock):
        from papaye.models import Package
        fake_response = Response(status=200, body='{"info": {"version": "1.0"}}')
        mock.return_value = fake_response

        # Test data
        package = factories.PackageFactory()

        result = Package.get_last_remote_version(False, package.name)

        self.assertEqual(mock.call_count, 0)
        self.assertIsNone(result)

    @patch('requests.get')
    def test_get_last_remote_version_with_proxy(self, mock):
        from papaye.models import Package
        fake_response = FakeGRequestResponse(status_code=200, content=b'{"info": {"version": "1.0"}}')
        mock.return_value = fake_response

        # Test data
        package = factories.PackageFactory()

        result = Package.get_last_remote_version(True, package.name)

        self.assertEqual(mock.call_count, 1)
        self.assertIsNotNone(result)
        self.assertEqual(result, '1.0')

    @patch('requests.get')
    def test_get_last_remote_version_with_proxy_404(self, mock):
        from papaye.models import Package
        fake_response = FakeGRequestResponse(status_code=404, content=b'{"info": {"version": "1.0"}}')
        mock.return_value = fake_response

        # Test data
        package = factories.PackageFactory()

        result = Package.get_last_remote_version(True, package.name)

        self.assertEqual(mock.call_count, 1)
        self.assertIsNone(result)

    def test_repository_is_up_to_date(self):
        release = factories.ReleaseFactory(version='1.0')
        package = release.package

        self.assertTrue(package.repository_is_up_to_date('1.0'))
        self.assertTrue(package.repository_is_up_to_date('0.9'))
        self.assertTrue(package.repository_is_up_to_date('1.0a'))
        self.assertFalse(package.repository_is_up_to_date('1.1'))
        self.assertFalse(package.repository_is_up_to_date('1.1a'))
        self.assertTrue(package.repository_is_up_to_date(''))
        self.assertTrue(package.repository_is_up_to_date(None))

    def test_by_name(self):
        from papaye.models import Package
        package = factories.PackageFactory(
            name='package1', root=self.root,
        )

        result = Package.by_name('package1', self.request)

        self.assertEqual(result, package)

    def test_by_name_not_found(self):
        from papaye.models import Package

        result = Package.by_name('package1', self.request)

        self.assertEqual(result, None)

    def test_get_last_release(self):
        package = factories.PackageFactory()
        factories.ReleaseFactory(release=package, version='1.0')
        factories.ReleaseFactory(package=package, version='2.0')

        result = package.get_last_release()

        self.assertEqual(result.version, '2.0')

    def test_get_last_release_with_minor(self):
        package = factories.PackageFactory()
        factories.ReleaseFactory(package=package, version='1.1')
        factories.ReleaseFactory(package=package, version='1.2')

        result = package.get_last_release()

        self.assertEqual(result.version, '1.2')

    def test_get_last_release_with_alpha(self):
        package = factories.PackageFactory()
        factories.ReleaseFactory(package=package, version='1.0')
        for minor in ['a1', 'a2', 'b1', 'b2', 'rc1']:
            factories.ReleaseFactory(
                package=package,
                version='1.0{}'.format(minor),
            )

        result = package.get_last_release()

        self.assertEqual(result.version, '1.0')

    def test_get_last_release_without_release(self):
        package = factories.PackageFactory()

        result = package.get_last_release()

        self.assertIsNone(result)

    def test_iter(self):
        release = factories.ReleaseFactory()
        package = release.package

        result = iter(package)

        assert isinstance(result, types.GeneratorType)
        assert list(result) == [release, ]

    def test_get_index(self):
        release = factories.ReleaseFactory()
        package = release.package

        result = package[0]

        assert result == release

    def test_get_index_bad(self):
        release = factories.ReleaseFactory()
        package = release.package

        result = package[1]

        assert result is None

    def test_get_item(self):
        release = factories.ReleaseFactory(version='1.0')
        package = release.package

        result = package['1.0']

        assert result == release

    def test_get_item_with_bad_release_name(self):
        release = factories.ReleaseFactory(version='1.0')
        package = release.package

        result = package['Bad release name']

        assert result is None


class ReleaseTest(unittest.TestCase):

    def setUp(self):
        self.request = get_current_request()
        self.root = factories.RootFactory()
        self.request.root = self.root


    def test_instantiate(self):
        from papaye.models import Release

        result = Release('1.0', metadata={})

        assert result.version == '1.0'
        assert result.metadata is not None

    def test_instantiate_local(self):
        from papaye.models import Release

        result = Release('1.0', metadata={})

        assert result.version == '1.0'
        assert result.metadata is not None

    def test_instantiante_without_deserialize_metadata(self):
        from papaye.models import Release

        result = Release(version='1.0', metadata={}, deserialize_metadata=False)

        assert result.version == '1.0'
        assert not hasattr(result, 'metadata')

    def test_by_packagename(self):
        from papaye.factories.root import repository_root_factory
        from papaye.models import Release
        root = repository_root_factory(self.request)
        package = factories.PackageFactory(root=root)
        release = factories.ReleaseFactory(version='1.0', package=package)

        result = Release.by_packagename(package.name, self.request)

        self.assertEqual(result, [release])

    def test_by_packagename_not_found(self):
        from papaye.models import Release

        result = Release.by_packagename('package1', self.request)
        self.assertEqual(result, None)

    def test_iter(self):
        from papaye.models import Release, ReleaseFile
        release = factories.ReleaseFactory(version='1.0')

        release_file = ReleaseFile('filename.tar.gz', b'')
        release['filename.tar.gz'] = release_file

        result = iter(release)

        assert isinstance(result, types.GeneratorType)
        assert list(result) == [release_file, ]

    def test_clone(self):
        from papaye.models import Release
        release = factories.ReleaseFactory(version='1.0')

        result = Release.clone(release)

        assert result is not release
        assert result.name == release.name
        assert result.version == release.version
        assert result.original_metadata == release.original_metadata
        assert result.metadata == release.metadata
        assert hasattr(result, 'release_files')
        assert len(list(result)) == len(list(release))

    def test_get_item(self):
        from papaye.models import Release, ReleaseFile
        release = factories.ReleaseFactory(version='1.0')
        release_file = ReleaseFile('filename.tar.gz', b'')
        release['filename.tar.gz'] = release_file

        result = release['filename.tar.gz']

        assert result == release_file

    def test_get_item_with_bad_releasefile_name(self):
        from papaye.models import Release, ReleaseFile
        release = factories.ReleaseFactory(version='1.0')
        release_file = ReleaseFile('filename.tar.gz', b'')
        release['filename.tar.gz'] = release_file

        result = release['bad releasefile name']

        assert result is None


class ReleaseFileTest(unittest.TestCase):

    def setUp(self):
        self.request = get_current_request()

    def test__init__(self):
        from papaye.models import ReleaseFile

        with open(get_resource('pyramid-1.5.tar.gz'), 'rb') as tar_gz:
            release_file = ReleaseFile('pyramid-1.5.tar.gz', tar_gz.read())

        self.assertEqual(release_file.size, 2413504)

    def test_instanciate(self):
        from papaye.models import ReleaseFile, STATUS

        with open(get_resource('pyramid-1.5.tar.gz'), 'rb') as tar_gz:
            result = ReleaseFile('release file', tar_gz.read())

        assert hasattr(result, 'status')
        assert result.status == STATUS.cached

    def test_instanciate_local(self):
        from papaye.models import ReleaseFile, STATUS

        with open(get_resource('pyramid-1.5.tar.gz'), 'rb') as tar_gz:
            result = ReleaseFile('release file', tar_gz.read(), status=STATUS.local)

        assert hasattr(result, 'status')
        assert result.status == STATUS.local

    def test_clone(self):
        from papaye.models import ReleaseFile
        with open(get_resource('pyramid-1.5.tar.gz'), 'rb') as tar_gz:
            release_file = ReleaseFile('pyramid-1.5.tar.gz', tar_gz.read())

        result = ReleaseFile.clone(release_file)

        assert result is not release_file
        assert result.filename == release_file.filename
        assert result.md5_digest == release_file.md5_digest
        assert result.upload_date == release_file.upload_date
        assert result.path == release_file.path
        assert result.content_type == release_file.content_type
        assert result.size == release_file.size
        assert id(result) != id(release_file)


class UserTest(unittest.TestCase):

    def setUp(self):
        self.request = testing.DummyRequest(matched_route=FakeRoute('simple'))
        self.blob_dir = set_database_connection(self.request)
        self.config = testing.setUp(request=self.request)

    def tearDown(self):
        remove_blob_dir(self.blob_dir)

    def test_hash_password(self):
        from papaye.models import User
        expected = 'b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb980b1d7785e5976ec049b46df5f1326af5a'
        expected += '2ea6d103fd07c95385ffab0cacbc86'

        result = User('a_user', 'password')
        self.assertEqual(result.password, expected)

    def test_by_username(self):
        from papaye.models import User
        from papaye.factories.root import user_root_factory

        root = user_root_factory(self.request)
        root['a_user'] = User('a_user', 'password')

        result = User.by_username('a_user', self.request)

        self.assertIsInstance(result, User)
        self.assertEqual(result.username, 'a_user')

    def test_by_username_without_result(self):
        from papaye.models import User

        result = User.by_username('a_user', self.request)

        self.assertIsNone(result)


class SubscriptableModelTest(unittest.TestCase):

    from papaye.models import SubscriptableBaseModel, Model

    class Model(SubscriptableBaseModel, Model):
        _subobjects_attr = 'attribute'

    def test_get(self):
        model_instance = self.Model(name='test')
        model_instance.attribute = {'test': 'ok'}

        result = model_instance.get('test')
        self.assertEqual(result, 'ok')

    def test_get_with_default(self):
        model_instance = self.Model(name='test')
        model_instance.attribute = {'test': 'ok'}

        result = model_instance.get('test', None)
        self.assertEqual(result, 'ok')

    def test_get_with_default_returned(self):
        model_instance = self.Model(name='name')
        model_instance.attribute = {'test': 'ok'}

        result = model_instance.get('oups', None)
        self.assertIsNone(result)


class BaseModelTest(unittest.TestCase):

    from papaye.models import Model, ClonableModelMixin

    class TestModel(ClonableModelMixin, Model):
        def __init__(self, attr1, attr2):
            self.attr1 = attr1
            self.attr2 = attr2

    def test_clone(self):
        model = self.TestModel('one', 'two')

        result = self.TestModel.clone(model)

        assert result is not model
        assert result.attr1 == 'one'
        assert result.attr2 == 'two'

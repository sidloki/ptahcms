import transaction
from zope import interface
import ptah, ptahcms
from ptah import config
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest
from pyramid.exceptions import ConfigurationConflictError


class RestBase(PtahTestCase):

    _allow = True
    _init_ptah = False
    _cleanup_mod = False
    _includes = ('ptahcms',)

    def _check_perm(self, perm, content, request=None, throw=False):
        return self._allow

    def _make_app(self):
        global ApplicationRoot
        class ApplicationRoot(ptahcms.ApplicationRoot):
            __type__ = ptahcms.Type('app')

        ApplicationRoot.__type__.cls = ApplicationRoot

        return ApplicationRoot

    def setUp(self):
        super(RestBase, self).setUp()

        self.orig_check_permission = ptah.check_permission
        ptah.check_permission = self._check_perm

    def tearDown(self):
        ptah.check_permission = self.orig_check_permission

        super(RestBase, self).tearDown()


class TestRestApi(RestBase):

    def test_rest_srv(self):
        from ptahcms import restsrv
        self.init_ptah()

        services = config.get_cfg_storage(restsrv.ID_REST)

        self.assertIn('cms', services)

        srv = services['cms']
        self.assertEqual(srv.title, 'Ptah CMS API')
        self.assertEqual(list(srv.actions.keys()),
                         ['content', 'applications', 'apidoc', 'types'])

    def test_rest_applications(self):
        from ptahcms.rest import cmsApplications

        ApplicationRoot = self._make_app()

        self.init_ptah()

        info = cmsApplications(self.request)
        self.assertEqual(info, [])

        factory = ptahcms.ApplicationFactory(
            ApplicationRoot, '/test', 'root', 'Root App', config=self.config)

        info = cmsApplications(self.request)
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]['__name__'], 'root')
        self.assertEqual(info[0]['__mount__'], 'test')
        self.assertEqual(info[0]['__link__'],
                         'http://example.com/content:%s/%s/'%(
                             info[0]['__mount__'], info[0]['__uri__']))

        ptahcms.ApplicationFactory(
            ApplicationRoot, '/test2', 'root2', 'Root App',config=self.config)
        self.assertEqual(len(cmsApplications(self.request)), 2)

        self._allow = False
        self.assertEqual(len(cmsApplications(self.request)), 0)

    def test_rest_applications_default(self):
        from ptahcms.rest import cmsApplications

        ApplicationRoot = self._make_app()

        self.init_ptah()

        info = cmsApplications(self.request)
        self.assertEqual(info, [])

        ptahcms.ApplicationFactory(
            ApplicationRoot, '/', 'root', 'Root App', config=self.config)

        info = cmsApplications(self.request)
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]['__name__'], 'root')
        self.assertEqual(info[0]['__mount__'], '')
        self.assertEqual(
            info[0]['__link__'],
            'http://example.com/content/%s/'%(info[0]['__uri__'],))

    def test_rest_types(self):
        from ptahcms.rest import cmsTypes

        self._make_app()
        self.init_ptah()

        info = cmsTypes(self.request)

        self.assertEqual(info[0]['name'], 'app')
        self.assertEqual(info[0]['__uri__'], 'type:app')
        self.assertEqual(len(info[0]['fieldset']), 2)
        self.assertEqual(info[0]['fieldset'][0]['name'], 'title')
        self.assertEqual(info[0]['fieldset'][1]['name'], 'description')

    def test_rest_content(self):
        from ptahcms.rest import cmsContent
        ApplicationRoot = self._make_app()
        self.init_ptah()

        request = DummyRequest(subpath=('content:root',))
        self.assertRaises(ptahcms.NotFound, cmsContent, request, 'root')

        request = DummyRequest(subpath=('content:test',),environ=self._environ)
        factory = ptahcms.ApplicationFactory(
            ApplicationRoot, '/test', 'root', 'Root App', config=self.config)
        root = factory(request)
        root.__uri__ = 'type-app:test'
        transaction.commit()

        self._allow = False
        self.assertRaises(ptahcms.Forbidden, cmsContent, request, 'test')

        self._allow = True

        root = factory(request)

        info = cmsContent(request, 'test')
        self.assertEqual(info['__uri__'], root.__uri__)

        self.assertRaises(ptahcms.NotFound,
                          cmsContent, request, 'test', action='unknown')

        info = cmsContent(request, 'test', root.__uri__)
        self.assertEqual(info['__uri__'], root.__uri__)

    def test_rest_content_default(self):
        from ptahcms.rest import cmsContent
        ApplicationRoot = self._make_app()
        self.init_ptah()

        request = DummyRequest(subpath=('content',), environ=self._environ)

        factory = ptahcms.ApplicationFactory(
            ApplicationRoot, '/', 'root', 'Root App', config=self.config)
        root = factory(request)
        root.__uri__ = 'type-app:test'
        transaction.commit()

        self._allow = False
        self.assertRaises(ptahcms.Forbidden, cmsContent, request)

        self._allow = True

        root = factory(request)

        info = cmsContent(request)
        self.assertEqual(info['__uri__'], root.__uri__)

        self.assertRaises(ptahcms.NotFound,
                          cmsContent, request, action='unknown')

        info = cmsContent(request, root.__uri__)
        self.assertEqual(info['__uri__'], root.__uri__)


class TestCMSRestAction(RestBase):

    def setUp(self):
        global Content, Container
        class Content(ptahcms.Content):
            __type__ = ptahcms.Type('content', 'Test Content')
            __uri_factory__ = ptah.UriFactory('cms-content')

        class Container(ptahcms.Container):
            __type__ = ptahcms.Type('container', 'Test Container')
            __uri_factory__ = ptah.UriFactory('cms-container')

        self.Content = Content
        self.Container = Container

        super(TestCMSRestAction, self).setUp()

    def test_rest_cms_action(self):
        from ptahcms.rest import IRestAction, IRestActionClassifier

        @ptahcms.restaction('my-update', Content, ptahcms.View)
        def update(content, request, *args):
            """ doc string """

        self.init_ptah()

        adapters = self.config.registry.adapters

        action = adapters.lookup(
            (IRestActionClassifier, interface.implementedBy(Content)),
            IRestAction, name='my-update')

        self.assertEqual(action.callable, update)
        self.assertEqual(action.name, 'my-update')
        self.assertEqual(action.description, update.__doc__)
        self.assertEqual(action.permission, ptahcms.View)

    def test_rest_cms_action_conflicts(self):
        @ptahcms.restaction('my-update', Content, ptahcms.View)
        def update1(content, request, *args):
            """ doc string """

        @ptahcms.restaction('my-update', Content, ptahcms.View)
        def update2(content, request, *args):
            """ doc string """

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_rest_cms_node_info(self):
        from ptahcms import rest
        self.init_ptah()

        content = Content()
        info = rest.nodeInfo(content, self.request)

        self.assertEqual(info['__uri__'], content.__uri__)
        self.assertEqual(
            info['__link__'],
            '%s%s/'%(self.request.application_url, content.__uri__))

    def test_rest_cms_apidoc(self):
        from ptahcms import rest
        self.init_ptah()

        content = Content()
        info = rest.apidocAction(content, self.request)
        self.assertEqual(len(info), 5)
        self.assertEqual(info[0]['name'], 'info')

        self._allow = False
        info = rest.apidocAction(content, self.request)
        self.assertEqual(len(info), 0)

    def test_rest_cms_container_info(self):
        from ptahcms import rest
        self.init_ptah()

        container = Container()
        container['content'] = Content()

        info = rest.containerNodeInfo(container, self.request)

        self.assertEqual(info['__uri__'], container.__uri__)
        self.assertEqual(
            info['__link__'],
            '%s%s/'%(self.request.application_url, container.__uri__))
        self.assertEqual(len(info['__contents__']), 1)
        self.assertEqual(info['__contents__'][0]['__uri__'],
                         container['content'].__uri__)

    def test_rest_cms_delete(self):
        from ptahcms import rest
        self.init_ptah()

        container = Container()
        container['content'] = Content()

        rest.deleteAction(container['content'], self.request)
        self.assertEqual(container.keys(), [])

    def test_rest_cms_update(self):
        from ptahcms import rest
        self.init_ptah()

        content = Content(title='Test')

        request = DummyRequest(params = {'title':''})
        info = rest.updateAction(content, request)
        self.assertEqual(info['errors']['title'], 'Required')

        request = DummyRequest(params = {'title':'New title'})

        info = rest.updateAction(content, request)
        self.assertEqual(
            info['__link__'],
            '%s%s/'%(request.application_url, content.__uri__))
        self.assertEqual(content.title, 'New title')

    def test_rest_cms_create(self):
        from ptahcms import rest
        self.init_ptah()

        all_types = ptah.get_types()

        all_types[Content.__type__.__uri__] = Content.__type__

        container = Container()

        request = DummyRequest(
            params = {'tinfo': Content.__type__.__uri__, 'name': 'content'},
            post = {'title':''})
        info = rest.createContentAction(container, request)
        self.assertEqual(info['errors']['title'], 'Required')

        request = DummyRequest(
            params = {'tinfo': Content.__type__.__uri__, 'name': 'content'},
            post = {'title':'New title'})

        rest.createContentAction(container, request)
        self.assertEqual(container.keys(), ['content'])
        self.assertEqual(container['content'].title, 'New title')

import transaction
from datetime import timedelta
from memphis import config
from memphis.form.interfaces import ICSRFService

from base import Base


class TestCsrf(Base):

    def tearDown(self):
        config.cleanUp(self.__class__.__module__)
        super(TestCsrf, self).tearDown()

    def test_csrf_service(self):
        import ptah
        from ptah.util import MemphisFormCSRFService
        
        self._init_memphis()

        csrf = config.registry.getUtility(ICSRFService)

        self.assertTrue(isinstance(csrf, MemphisFormCSRFService))

        t = csrf.generate('test')

        self.assertEqual(csrf.get(t), 'test')
        self.assertEqual(csrf.generate('test'), t)

        csrf.remove(t)
        self.assertEqual(csrf.get(t), None)
        
        t2 = csrf.generate('test')
        self.assertTrue(t != t2)


import unittest
import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, RequestError


XML_DOC = """<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""


class ProcessorTest(SeisHubEnvironmentTestCase):
    
    def test_process(self):
        request = Processor(self.env)
        request.path = '/'
        # test invalid methods
        for method in ['HEAD','XXX']:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.NOT_ALLOWED)
        # test a valid method
        request.method = 'get'
        request.process()
    
    def test_processRoot(self):
        request = Processor(self.env)
        request.path = '/'
        # test forbidden methods
        for method in ['POST','PUT','DELETE']:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.FORBIDDEN)
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # root should return a dict
        self.assertTrue(isinstance(data, dict))
        # should have at least 'package' and 'property' as keys
        self.assertTrue(data.has_key('package'))
        self.assertTrue(isinstance(data.get('package'),list))
        self.assertTrue(data.has_key('property'))
        self.assertTrue(isinstance(data.get('property'),list))
        # check default entries
        self.assertTrue('/seishub' in data.get('package'))
    
    def test_processPackage(self):
        request = Processor(self.env)
        request.path = '/seishub'
        # test forbidden methods
        for method in ['POST','PUT','DELETE']:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.FORBIDDEN)
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # package should return a dict
        self.assertTrue(isinstance(data, dict))
        # should have 'resourcetype', 'alias', 'mapping' and 'property'
        self.assertTrue(data.has_key('resourcetype'))
        self.assertTrue(isinstance(data.get('resourcetype'),list))
        self.assertTrue(data.has_key('alias'))
        self.assertTrue(isinstance(data.get('alias'),list))
        self.assertTrue(data.has_key('mapping'))
        self.assertTrue(isinstance(data.get('mapping'),list))
        self.assertTrue(data.has_key('property'))
        self.assertTrue(isinstance(data.get('property'),list))
        # check default entries
        self.assertTrue('/seishub/schema' in data.get('resourcetype'))
        self.assertTrue('/seishub/stylesheet' in data.get('resourcetype'))
    
    def test_processResourceType(self):
        request = Processor(self.env)
        request.path = '/seishub/schema'
        # test forbidden methods
        for method in ['POST','DELETE']:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.FORBIDDEN)
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # package should return a dict
        self.assertTrue(isinstance(data, dict))
        # should have at least 'index', 'alias', 'mapping' and 'property'
        self.assertTrue(data.has_key('index'))
        self.assertTrue(isinstance(data.get('index'),list))
        self.assertTrue(data.has_key('alias'))
        self.assertTrue(isinstance(data.get('alias'),list))
        self.assertTrue(data.has_key('mapping'))
        self.assertTrue(isinstance(data.get('mapping'),list))
        self.assertTrue(data.has_key('property'))
        self.assertTrue(isinstance(data.get('property'),list))
        # check default entries
        self.assertTrue('/seishub/schema/.all' in data.get('property'))
        # test valid PUT method
        request.method = 'PUT'
        request.content = StringIO.StringIO(XML_DOC)
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.CREATED)
        self.assertTrue(isinstance(request.response_header, dict))
        response_header = request.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(request.path))
        # fetch all resources via property .all
        request.method = 'GET'
        request.path = '/seishub/schema/.all'
        data = request.process()
        # only resources should be there
        self.assertTrue(data.has_key('resource'))
        self.assertTrue(isinstance(data.get('resource'),list))
        self.assertTrue(location in data.get('resource'))
        # fetch resource and compare it with original
        request.path = location
        data = request.process()
        self.assertTrue(data, XML_DOC)
        # delete uploaded resource
        request.method = 'DELETE'
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.NO_CONTENT)
    
    def test_deleteResource(self):
        request = Processor(self.env)
        request.method = 'DELETE'
        # id is no integer
        request.path = '/seishub/schema/idisnointeger'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.FORBIDDEN)
        # package and/or resource type does not exists
        request.path = '/xxx/yyy/1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.FORBIDDEN)
        # id does not exists
        request.path = '/seishub/schema/-1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.INTERNAL_SERVER_ERROR)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
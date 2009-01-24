# -*- coding: utf-8 -*-
"""
A test suite for B{GET} request on REST resources.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import registerIndex
from seishub.processor import PUT, POST, DELETE, GET, Processor
from seishub.processor.resources.rest import RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


XML_BASE_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>%s</blahblah1>
    <blah2>%s</blah2>
  </blah1>
</testml>"""

CDATA = """<![CDATA[ &<
>&]]>"""

XML_DOC = XML_BASE_DOC % ("üöäß", "5")
XML_DOC2 = XML_BASE_DOC % ("üöäß", "%d")
XML_DOC3 = XML_BASE_DOC % (CDATA, "5")
XML_DOC4 = XML_BASE_DOC % ("%s", "egal")


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'property-test'
    resourcetype_id = 'notvc'
    version_control = False
    registerIndex('/testml/blah1/blahblah1', 'text')


class AResourceType2(Component):
    """
    A non versioned test resource type for datetime index tests.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'property-test'
    resourcetype_id = 'notvc2'
    version_control = False
    registerIndex('/testml/blah1/blahblah1', 'datetime')

class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'property-test'
    resourcetype_id = 'vc'
    version_control = True
    registerIndex('/testml/blah1/blah2', 'text')


class RestPropertyTests(SeisHubEnvironmentTestCase):
    """
    A test suite for GET request on REST resources.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.enableComponent(AResourceType2)
        self.env.tree = RESTFolder()
    
    def tearDown(self):
        self.env.catalog.removeIndex('property-test', 'notvc', 
                                     '/testml/blah1/blahblah1')
        self.env.catalog.removeIndex('property-test', 'notvc2', 
                                     '/testml/blah1/blahblah1')
        self.env.catalog.removeIndex('property-test', 'vc', '/testml/blah1/blah2')
        self.env.registry.db_deleteResourceType('property-test', 'notvc')
        self.env.registry.db_deleteResourceType('property-test', 'notvc2')
        self.env.registry.db_deleteResourceType('property-test', 'vc')
        self.env.registry.db_deletePackage('property-test')
    
    def test_getResourceIndex(self):
        """
        Tests resource index property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/property-test/notvc/test.xml', StringIO(XML_DOC))
        # get index XML w/o trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML w/ trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML on revision 1 w/o trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/1/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML on revision 1 w/ trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/1/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # remove resource
        proc.run(DELETE, '/property-test/notvc/test.xml')
    
    def test_getRevisionIndex(self):
        """
        Tests revision index property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/property-test/vc/test.xml/', StringIO(XML_DOC2 % 12))
        proc.run(POST, '/property-test/vc/test.xml/', StringIO(XML_DOC2 % 234))
        proc.run(POST, '/property-test/vc/test.xml/', StringIO(XML_DOC2 % 3456))
        # get index XML of latest revision w/o trailing slash
        res = proc.run(GET, '/property-test/vc/test.xml/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of revision 3 w/o trailing slash
        res = proc.run(GET, '/property-test/vc/test.xml/3/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of latest revision w/ trailing slash
        res = proc.run(GET, '/property-test/vc/test.xml/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of revision 3 w/ trailing slash
        res = proc.run(GET, '/property-test/vc/test.xml/3/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # remove resource
        proc.run(DELETE, '/property-test/vc/test.xml')
    
    def test_getResourceMetaData(self):
        """
        Tests resource meta data property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/property-test/notvc/test.xml', StringIO(XML_DOC))
        # get meta data XML w/o trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>notvc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # get meta data XML w/ trailing slash
        res = proc.run(GET, '/property-test/notvc/test.xml/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>notvc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # remove resource
        proc.run(DELETE, '/property-test/notvc/test.xml')
    
    def test_getRevisionMetaData(self):
        """
        Tests revision meta data property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/property-test/vc/test.xml', StringIO(XML_DOC2 % 12))
        proc.run(POST, '/property-test/vc/test.xml', StringIO(XML_DOC2 % 234))
        proc.run(POST, '/property-test/vc/test.xml', StringIO(XML_DOC2 % 3456))
        # get meta data XML w/o trailing slash from latest revision
        res = proc.run(GET, '/property-test/vc/test.xml/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>3</revision>' in data)
        # get meta data XML w/ trailing slash from latest revision
        res = proc.run(GET, '/property-test/vc/test.xml/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>3</revision>' in data)
        # get meta data XML w/o trailing slash from 1. revision
        res = proc.run(GET, '/property-test/vc/test.xml/1/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # get meta data XML w/ trailing slash from 1. revision
        res = proc.run(GET, '/property-test/vc/test.xml/1/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>property-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # remove resource
        proc.run(DELETE, '/property-test/vc/test.xml')
    
    def test_indexWithCDATASection(self):
        """
        Test indexing a XML tag with a CDATA section.
        
        CDATA will be striped for indexed values. Requesting such a indexed
        value results into a XML conform UTF-8 encoded string. Also entities 
        such as the "&" (amperson) will be mapped with "&amp;".
        
        @see: L{http://codespeak.net/lxml/api.html#cdata}.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/property-test/notvc/1', StringIO(XML_DOC3))
        data = proc.run(GET, '/property-test/notvc/1/.index/').render_GET(proc)
        self.assertTrue("<value> &amp;&lt;\n&gt;&amp;</value>" in data)
        # delete resource
        proc.run(DELETE, '/property-test/notvc/1')
    
    def test_validDateTimeIndexes(self):
        """XXX: Fails yet - see #108 and #107.
        Test indexing of XML documents with valid datetime fields.
        """
        proc = Processor(self.env)
        # w/ T
        xml_doc = XML_DOC4 % "2009-12-20T12:12:21"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # w/o T
        xml_doc = XML_DOC4 % "2009-12-20 12:12:21"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # milliseconds, w/ T
        xml_doc = XML_DOC4 % "2009-12-20T12:12:21.123456"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21.123456</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # milliseconds, w/o T
        xml_doc = XML_DOC4 % "2009-12-20 12:12:21.123456"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21.123456</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # limited milliseconds, w/ T
        xml_doc = XML_DOC4 % "2009-12-20T12:12:21.123"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21.123000</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # limited milliseconds, w/o T
        xml_doc = XML_DOC4 % "2009-12-20 12:12:21.123"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20 12:12:21.123000</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
        # date only
        # XXX: this should be indexed right without error message
        xml_doc = XML_DOC4 % "2009-12-20"
        proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
        data = proc.run(GET, '/property-test/notvc2/1/.index').render_GET(proc)
        self.assertTrue("<value>2009-12-20</value>" in data)
        proc.run(DELETE, '/property-test/notvc2/1')
    
    def test_invalidDateTimeIndexes(self):
        """XXX: Fails yet - see #107.
        Test indexing of XML documents with invalid datetime fields.
        """
        proc = Processor(self.env)
        # invalid date 
        xml_doc = XML_DOC4 % "2009-20-12"
        try:
            proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # invalid datetime 
        xml_doc = XML_DOC4 % "2009-20-12T12:12:20"
        try:
            proc.run(PUT, '/property-test/notvc2/1', StringIO(xml_doc))
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.CONFLICT)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestPropertyTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
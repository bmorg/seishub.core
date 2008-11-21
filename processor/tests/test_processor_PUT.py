# -*- coding: utf-8 -*-

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor import PUT, POST, DELETE, GET, Processor
from seishub.test import SeisHubEnvironmentTestCase
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


XML_VCDOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """A non versioned test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'put-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'put-test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorPUTTest(SeisHubEnvironmentTestCase):
    """Processor test case."""
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_putOnDeletedVersionControlledResource(self):
        """PUT on deleted versionized resource should create new resource."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/xml/put-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/xml/put-test/vc/test.xml', StringIO(XML_VCDOC % 2))
        proc.run(POST, '/xml/put-test/vc/test.xml', StringIO(XML_VCDOC % 3))
        # delete resource
        proc.run(DELETE, '/xml/put-test/vc/test.xml')
        # upload again
        proc.run(PUT, '/xml/put-test/vc/test.xml', StringIO(XML_VCDOC % 10))
        # should be only latest upload
        data=proc.run(GET, '/xml/put-test/vc/test.xml/1')
        self.assertEqual(data, XML_VCDOC % 10)
        # delete resource
        proc.run(DELETE, '/xml/put-test/vc/test.xml')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorPUTTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
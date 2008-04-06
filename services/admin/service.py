# -*- coding: utf-8 -*-

import os
import string
from urllib import unquote

from twisted.web import static, http, util as webutil
from twisted.internet import threads, defer, ssl
from twisted.application import internet
from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import ExtensionPoint, SeisHubError
from seishub.defaults import DEFAULT_ADMIN_PORT, \
                             DEFAULT_HTTPS_CERTIFICATE_FILENAME, \
                             DEFAULT_HTTPS_PRIVATE_KEY_FILENAME
from seishub.config import IntOption, Option


class AdminRequest(http.Request):
    """A HTTP request."""
    
    def __init__(self, *args, **kw):
        http.Request.__init__(self, *args, **kw)
        self._initAdminPanels()
        self._initStaticContent()
    
    def process(self):
        # post process self.path
        self.postpath = map(unquote, string.split(self.path[1:], '/'))
        
        # process static content
        if self.path in self.static_content.keys():
            self.static_content.get(self.path).render(self)
            self.finish()
            return
        
        # redirect if only category given or web root
        if len(self.postpath)<2:
            categories = [p[0] for p in self.panel_ids]
            if self.postpath and self.postpath[0] in categories:
                # ok there is a category - redirect to first sub panel
                pages = filter(lambda p: p[0] == self.postpath[0], 
                               self.panel_ids)
                menuitems = [p[2] for p in pages]
                menuitems.sort()
                self.redirect('/'+pages[0][0]+'/'+menuitems[0])
                self.finish()
                return
            # redirect to the available panel
            self.redirect('/'+self.panel_ids[0][0]+'/'+self.panel_ids[0][2])
            self.finish()
            return
        
        # now it should be an AdminPanel
        self.cat_id = self.postpath[0]
        self.panel_id = self.postpath[1]
        
        self.panel = self.panels.get((self.cat_id, self.panel_id), None)
        if not self.panel:
            self.redirect('/'+self.panel_ids[0][0]+'/'+self.panel_ids[0][2])
            self.finish()
            return
        
        # get content in a extra thread and render after completion
        d = threads.deferToThread(self.panel.renderPanel, self) 
        d.addCallback(self._renderPanel)
        d.addErrback(self._processingFailed) 
        return
    
    def _renderPanel(self, result):
        if not result or isinstance(result, defer.Deferred):
            return
        template, data = result
        
        # no template given
        if not template:
            self.write(data)
            self.finish()
            return
        
        body = ''
        for path in self._getTemplateDirs():
            filename = path + os.sep + template
            if not os.path.isfile(filename):
                continue
            body = Template(file=filename, searchList=[data]) 
        
        # process template
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "index.tmpl"))
        temp.navigation = self._renderNavigation()
        temp.submenu = self._renderSubMenu()
        temp.version = SEISHUB_VERSION
        temp.content = body
        temp.error = self._renderError(data)
        body = str(temp)
        
        # set various default headers
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        self.setHeader('content-type', "text/html; charset=UTF-8")
        self.setHeader('content-length', str(len(body)))
        
        # write content
        self.write(body)
        self.finish()
    
    def _renderError(self, data):
        """Render an error message."""
        if not data.get('error', None) and not data.get('exception', None):
            return
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "error.tmpl"))
        msg = data.get('error', '')
        if isinstance(msg, basestring):
            temp.message = msg
            temp.exception = None
        elif isinstance(msg, tuple) and len(msg)==2:
            temp.message = str(msg[0])
            temp.exception = str(msg[1])
        else:
            temp.message = str(msg)
            temp.exception = None
        return temp
    
    def _renderNavigation(self):
        """Generate the main navigation bar."""
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "navigation.tmpl"))
        menuitems = [(i[0],i[1]) for i in self.panel_ids]
        menuitems = dict(menuitems).items()
        menuitems.sort()
        temp.navigation = menuitems
        temp.cat_id = self.cat_id
        return temp
    
    def _renderSubMenu(self):
        """Generate the sub menu box."""
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "submenu.tmpl"))
        menuitems = map((lambda p: (p[2],p[3])),
                         filter(lambda p: p[0]==self.cat_id, self.panel_ids))
        menuitems = dict(menuitems).items()
        menuitems.sort()
        temp.submenu = menuitems
        temp.cat_id = self.cat_id
        temp.panel_id = self.panel_id
        return temp
    
    def _processingFailed(self, reason):
        self.env.log.error('Exception rendering:', reason)
        body = ("<html><head><title>web.Server Traceback (most recent call "
                "last)</title></head><body><b>web.Server Traceback (most "
                "recent call last):</b>\n\n%s\n\n</body></html>\n"
                % webutil.formatFailure(reason))
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.setHeader('content-type',"text/html")
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        return reason
    
    def _getTemplateDirs(self):
        """Returns a list of searchable template directories."""
        dirs = [resource_filename(self.__module__, "templates")]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]
    
    def _initAdminPanels(self):
        """Return a list of available admin panels."""
        panel_list = ExtensionPoint(IAdminPanel).extensions(self.env)
        self.panel_ids = []
        self.panels = {}
        
        for panel in panel_list:
            # skip panels without proper interfaces
            if not hasattr(panel, 'getPanelId') or \
               not hasattr(panel, 'renderPanel'):
                continue;
            options = panel.getPanelId()
            # getPanelId has exact 4 values in a tuple
            if not isinstance(options, tuple) or len(options)!=4:
                continue
            self.panels[(options[0], options[2])] = panel
            self.panel_ids.append(options)
        
        def _orderPanelIds(p1, p2):
            if p1[0] == 'general':
                if p2[0] == 'general':
                    return cmp(p1[1:], p2[1:])
                return -1
            elif p2[0] == 'general':
                if p1[0] == 'general':
                    return cmp(p1[1:], p2[1:])
                return 1
            return cmp(p1, p2)
        self.panel_ids.sort(_orderPanelIds)
    
    def _initStaticContent(self):
        """Returns a dictionary of static web resources."""
        default_css = static.File(resource_filename(self.__module__,
                                                    "htdocs"+os.sep+"css"+ \
                                                    os.sep+"default.css"))
        default_ico = static.File(resource_filename(self.__module__,
                                                    "htdocs"+os.sep+\
                                                    "favicon.ico"),
                                  defaultType="image/x-icon")
        default_js = static.File(resource_filename(self.__module__,
                                                   "htdocs"+os.sep+"js"+ \
                                                   os.sep+"default.js"))
        quake_gif = static.File(resource_filename(self.__module__,
                                                  "htdocs"+os.sep+"images"+ \
                                                  os.sep+"quake.gif"))
        # default static files
        self.static_content = {'/css/default.css': default_css,
                               '/js/default.js': default_js,
                               '/favicon.ico': default_ico,
                               '/images/quake.gif': quake_gif,}
        
        # add panel specific static files
        for panel in self.panels.values():
            if hasattr(panel, 'getHtdocsDirs'):
                items = panel.getHtdocsDirs()
                for path, child in items:
                    self.static_content[path] = static.File(child)


class AdminHTTPChannel(http.HTTPChannel):
    """A receiver for HTTP requests."""
    requestFactory = AdminRequest
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class AdminServiceFactory(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = AdminHTTPChannel
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


class AdminService(internet.SSLServer):
    """Service for WebAdmin HTTP Server."""
    IntOption('admin', 'port', DEFAULT_ADMIN_PORT, "WebAdmin port number.")
    Option('admin', 'private_key_file', DEFAULT_HTTPS_PRIVATE_KEY_FILENAME, 
           "Private key file.")
    Option('admin', 'certificate_file', DEFAULT_HTTPS_CERTIFICATE_FILENAME, 
           "Certificate file.")
    Option('admin', 'secured', 'True', "Enable HTTPS connection.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('admin', 'port')
        secured = env.config.getbool('admin', 'secured')
        priv, cert = self._getCertificates()
        if secured:
            ssl_context = ssl.DefaultOpenSSLContextFactory(priv, cert)
            internet.SSLServer.__init__(self, port, AdminServiceFactory(env),\
                                        ssl_context)
        else:
            self.method = 'TCP'
            internet.SSLServer.__init__(self, port, AdminServiceFactory(env),1)
        self.setName("WebAdmin")
        self.setServiceParent(env.app)
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        priv = self.env.config.get('admin', 'private_key_file') or \
               DEFAULT_HTTPS_PRIVATE_KEY_FILENAME
        cert = self.env.config.get('admin', 'certificate_file') or \
               DEFAULT_HTTPS_CERTIFICATE_FILENAME
        if not os.path.isfile(priv):
            priv = os.path.join(self.env.path, 'conf', priv)
            if not os.path.isfile(priv):
                raise SeisHubError('Missing file ' + priv)
        if not os.path.isfile(cert):
            cert = os.path.join(self.env.path, 'conf', cert)
            if not os.path.isfile(cert):
                raise SeisHubError('Missing file ' + cert)
        return priv, cert
        
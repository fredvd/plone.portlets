=====================
Plone Portlets Engine
=====================

This package contains the basic interfaces and generalisable code for managing
dynamic portlets. Portlets are content provider (see zope.contentprovider) 
which are assigned to columns or other areas (represented by a portlet manager). 

The portlets infrastructure is similar to zope.viewlet, but differs in that
it is dynamic. Rather than register viewlets that "plug into" a viewlet manager
in ZCML, plone.portlets contains the basis for portlets that are assigned - 
persistently, at run time - to locations, users or groups.

The remainder of this file will explain the API and components in detail, but
in general, the package is intended to be used as follows:

- The application layer registers a generic adapter to IPortletContext. Any
context where portlets may be assigned needs to be adaptable to this interface.

- Any number of PortletManager's are stored persistently. A PortletManager is
a storage for portlet assignments, keyed by context, user or group. 

- At a local site, an adapter registration is made for each instance of 
PortletManager with a particular name (e.g. "plone.leftcolumn"), adapting
(context, request, view) to IContentProvider. The PortletManager instance 
will act as the adapter factory by virtue of its __call__() method to return
a PortletManagerRenderer, which provides IContentProvider.

- Once this registration is made, any template in that site would be able to
write e.g. tal:replace="structure provider:plone.leftcolumn" to see the 
context-dependent rendering of that particular viewlet manager.

Actual portlets are described by three interfaces, which may be kept separate or
implemented in the same component, depending on the use case.

- IPortletDataProvider is a marker interface for objects that provide 
configuration information for how a portlet should be rendered. This may be
an existing content object, or something specific to a portlet.

- A special type content provider, IPortletRenderer, knows how to render each 
type of portlet. The IPortletRenderer should be a multi-adapter from 
(context, request, view, portlet manager, data provider).

- An IPortletAssignment is a persistent object that can be instantiated and
is stored by an IPortletManager. The assignment will return a handle to an 
IPortletDataProvider.

Typically, you will either have a specific IPortletAssignment for a specific
IPortletDataProvider, or a generic IPortletAssignment for different types of
IPortletDataProvider. You will also typically have a generalisable 
IPortletRenderer for each type of IPortletDataProvider.

The examples below demonstrate a "specific-specific" portlet in the form of a 
login portlet - here, the same object provides both the assignment and the data 
provider aspect - and a "generic-generic" portlet, where a generic 
IPortletAssignment knows how to reference a content object, with different 
content objects potentially having different types of IPortletRenderers for 
rendering.

The portlet context
-------------------

We will create a test environment first, consisting of content objects (folders
and documents) that have a unique id managed by a global UID registry. For
the purposes of testing, we simply use the python id() for this, though this
is obviously not a realistic implementation (since it is non-persistent and
instance-specific). The environment also knows the id of the current user and 
that user's groups.

  >>> from zope.interface import implements, Interface
  >>> from zope.component import adapts, provideAdapter
  >>> from zope import schema
  
  >>> from zope.app.container.interfaces import IContained
  >>> from zope.app.folder import rootFolder, Folder
  
  >>> testUIDRegistry = {}
  >>> testUser = 'TestUser'
  >>> testUserGroups = ('TestGroup1', 'TestGroup2',)
  
Now we can provide an IPortletContext for this environment.

  >>> from plone.portlets.interfaces import IPortletContext
  >>> class TestPortletContext(object):
  ...     implements(IPortletContext)
  ...     adapts(Interface)
  ...
  ...     def __init__(self, context):
  ...         self.context = context
  ...
  ...     @property
  ...     def uid(self):
  ...         return id(self.context)
  ...
  ...     @property
  ...     def parent(self):
  ...         return self.context.__parent__
  ...
  ...     @property
  ...     def userId(self):
  ...         return testUser
  ...
  ...     @property
  ...     def groupIds(self):
  ...         return testUserGroups
  >>> provideAdapter(TestPortletContext)
  
We create a sample content heirarchy as well, to be used later. We register the
objects with our contrived UID registry, so that the generic portlet context
will work for all of them.
  
  >>> class ITestDocument(IContained):
  ...     text = schema.TextLine(title=u"Text to render")
  >>> class TestDocument(object):
  ...     implements(ITestDocument)
  ...
  ...     def __init__(self, text=u''):
  ...         self.__name__ = None
  ...         self.__parent__ = None
  ...         self.text = text
  
  >>> rootFolder =  rootFolder()
  >>> testUIDRegistry[id(rootFolder)] = rootFolder

  >>> rootFolder['child1'] = Folder()
  >>> testUIDRegistry[id(rootFolder['child1'])] = rootFolder['child1']
  
  >>> rootFolder['child2'] = Folder()
  >>> testUIDRegistry[id(rootFolder['child2'])] = rootFolder['child2']
  
  >>> rootFolder['doc1'] = TestDocument(u'Doc one')
  >>> testUIDRegistry[rootFolder['doc1']] = rootFolder['doc1']
  
We also turn our root folder into a site, so that we can make local 
registrations on it.

  >>> from zope.app.component.interfaces import ISite
  >>> from zope.component.persistentregistry import PersistentComponents
  >>> rootFolder.setSiteManager(PersistentComponents())
  >>> ISite.providedBy(rootFolder)
  True
  
Registering portlet managers
----------------------------

Portlet managers are persistent objects that contain portlet assignments. They
are registered as adapter factories which allows them to be looked up in a
'provider:' TALES expression. We place two portlet managers inside our site,
although they are not registered as part of the portlet context (i.e. they
do not use the testing UID registry).

  >>> from plone.portlets.manager import PortletManager
  >>> rootFolder['columns'] = Folder()
  >>> rootFolder['columns']['left'] = PortletManager()
  >>> rootFolder['columns']['right'] = PortletManager()
  
Then we register the managers as adapter factories for their content providers,
using the site manager defined above.

  >>> from plone.portlets.interfaces import IPortletManagerRenderer
  >>> from zope.publisher.interfaces.browser import IBrowserRequest
  >>> from zope.publisher.interfaces.browser import IDefaultBrowserLayer
  >>> from zope.publisher.interfaces.browser import IBrowserView
  >>> sm = rootFolder.getSiteManager()
  >>> sm.registerAdapter(required=(Interface, IBrowserRequest, IBrowserView), 
  ...                    provided=IPortletManagerRenderer, 
  ...                    name='columns.left', 
  ...                    factory=rootFolder['columns']['left'])
  >>> sm.registerAdapter(required=(Interface, IBrowserRequest, IBrowserView), 
  ...                    provided=IPortletManagerRenderer, 
  ...                    name='columns.right', 
  ...                    factory=rootFolder['columns']['right'])
  
We should now be able to get this via a provider: expression (these lines
borrowed from zope.contentprovider).

  >>> import os, tempfile
  >>> tempDir = tempfile.mkdtemp()
  >>> templateFileName = os.path.join(tempDir, 'template.pt')
  >>> open(templateFileName, 'w').write("""
  ... <html>
  ...   <body>
  ...     <h1>My Web Page</h1>
  ...     <div class="left-column">
  ...       <tal:block replace="structure provider:columns.left" />
  ...     </div>
  ...     <div class="main">
  ...       Content here
  ...     </div>
  ...   </body>
  ... </html>
  ... """)
  
We register the template as a view for all objects.

  >>> from zope.app.pagetemplate.simpleviewclass import SimpleViewClass
  >>> FrontPage = SimpleViewClass(templateFileName, name='main.html')

  >>> provideAdapter(FrontPage, (Interface, IDefaultBrowserLayer,), 
  ...                   Interface, name='main.html')

Create a document that we can view.

  >>> doc1 = TestDocument()

Look up the view and render it. Note that the portlet manager is still empty
(no portlets have been assigned), so nothing will be displayed yet.

  >>> from zope.publisher.browser import TestRequest
  >>> request = TestRequest()

  >>> from zope.component import getMultiAdapter
  >>> view = getMultiAdapter((doc1, request), name='main.html')
  >>> print view().strip()
  <html>
    <body>
      <h1>My Web Page</h1>
      <div class="left-column">
        
      </div>
      <div class="main">
        Content here
      </div>
    </body>
  </html>
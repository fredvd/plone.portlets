from zope.interface import implements
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import UpdateNotCalled

from plone.portlets.interfaces import IPortletContext
from plone.portlets.interfaces import IPortletRetriever
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPlacelessPortletManager
from plone.portlets.interfaces import IPortletManagerRenderer
from plone.portlets.interfaces import IPortletRenderer

from plone.portlets.storage import PortletStorage

class PortletManagerRenderer(object):
    """Default renderer for portlet managers.

    When the zope.contentprovider handler for the provider: expression looks up
    a name, context, it will find an adapter factory that creates an instance
    of this class. In fact, this will be a site-local registration, and the
    actual implementation of the adapter factory will be the (persistent)
    IPortletManager, which has a suitable __call__() method.
    """
    implements(IPortletManagerRenderer)

    def __init__(self, manager, context, request, view):
        self.__parent__ = view
        self.manager = manager
        self.context = context
        self.request = request
        self.template = None
        self.__updated = False

    def filter(self, portlets):
        return [p for p in portlets if p.available]

    def update(self):
        self.__updated = True

        portletContext = IPortletContext(self.context)
        retriever = getMultiAdapter((portletContext, self.manager), IPortletRetriever)

        self.portlets = [self._dataToPortlet(a.data)
                            for a in self.filter(retriever.getPortlets())]

        for p in self.portlets:
            p.update()

    def render(self):
        if not self.__updated:
            raise UpdateNotCalled()
        if self.template:
            return self.template(portlets=self.portlets)
        else:
            return u'\n'.join([p.render() for p in self.portlets])

    def _dataToPortlet(self, data):
        """Helper method to get the correct IPortletRenderer for the given
        data object.
        """
        return getMultiAdapter((self.context, self.request, self.__parent__,
                                    self.manager, data,), IPortletRenderer)


class PortletManager(PortletStorage):
    """Default implementation of the portlet manager.

    Provides the functionality that allows the portlet manager to act as an
    adapter factory.
    """

    implements(IPortletManager)

    __name__ = __parent__ = None

    def __call__(self, context, request, view):
        return PortletManagerRenderer(self, context, request, view)
        
class PlacelessPortletManager(PortletManager):
    """Default implementation of a placeless portlet manager.
    
    This exists mainly to allow a different adapter for IPortletRetriever
    to be found.
    """
    
    implements(IPlacelessPortletManager)

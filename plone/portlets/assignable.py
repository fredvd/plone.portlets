from persistent.dict import PersistentDict

from zope.interface import implements, implementer
from zope.component import adapts, adapter
from zope.annotation.interfaces import IAnnotations

from plone.portlets.interfaces import ILocalPortletAssignmentManager
from plone.portlets.interfaces import IPortletAssignmentMapping
from plone.portlets.interfaces import ILocalPortletAssignable
from plone.portlets.interfaces import IPortletManager

from plone.portlets.storage import PortletAssignmentMapping
from plone.portlets.constants import CONTEXT_ASSIGNMENT_KEY
from plone.portlets.constants import CONTEXT_BLACKLIST_STATUS_KEY
from plone.portlets.constants import CONTEXT_CATEGORY

from BTrees.OOBTree import OOBTree

@adapter(ILocalPortletAssignable, IPortletManager)
@implementer(IPortletAssignmentMapping)
def localPortletAssignmentMappingAdapter(context, manager):
    """When adapting (context, manager), get an IPortletAssignmentMapping
    by finding one in the object's annotations. The container will be created
    if necessary.
    """
    annotations = IAnnotations(context)
    local = annotations.get(CONTEXT_ASSIGNMENT_KEY, None)
    if local is None:
        local = annotations[CONTEXT_ASSIGNMENT_KEY] = OOBTree()
    portlets = local.get(manager.__name__, None)
    if portlets is None:
        portlets = local[manager.__name__] = PortletAssignmentMapping(manager=manager.__name__,
                                                                      category=CONTEXT_CATEGORY)
    return portlets
    

class LocalPortletAssignmentManager(object):
    """Default implementation of ILocalPortletAssignmentManager which stores
    information in an annotation.
    """
    implements(ILocalPortletAssignmentManager)
    adapts(ILocalPortletAssignable, IPortletManager)

    def __init__(self, context, manager):
        self.context = context
        self.manager = manager

    def setBlacklistStatus(self, category, status):
        blacklist = self._getBlacklist(True)
        blacklist[category] = status
    
    def getBlacklistStatus(self, category):
        blacklist = self._getBlacklist(False)
        if blacklist is None:
            return None
        return blacklist.get(category, None)
        
    def _getBlacklist(self, create=False):
        annotations = IAnnotations(self.context)
        local = annotations.get(CONTEXT_BLACKLIST_STATUS_KEY, None)
        if local is None:
            if create:
                local = annotations[CONTEXT_BLACKLIST_STATUS_KEY] = PersistentDict()
            else:
                return None
        blacklist = local.get(self.manager.__name__, None)
        if blacklist is None:
            if create:
                blacklist = local[self.manager.__name__] = PersistentDict()
            else:
                return None
        return blacklist
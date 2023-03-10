from zope.interface import implements, Interface
from zope.component import adapts
from zope.annotation.interfaces import IAnnotations

from plone.portlets.interfaces import IPortletContext
from plone.portlets.interfaces import ILocalPortletAssignable
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPlacelessPortletManager
from plone.portlets.interfaces import IPortletRetriever

from plone.portlets.constants import CONTEXT_ASSIGNMENT_KEY
from plone.portlets.constants import CONTEXT_BLACKLIST_STATUS_KEY

from plone.portlets.constants import CONTEXT_CATEGORY

class PortletRetriever(object):
    """The default portlet retriever.

    This will examine the context and its parents for contextual portlets,
    provided they provide ILocalPortletAssignable.
    """

    implements(IPortletRetriever)
    adapts(Interface, IPortletManager)

    def __init__(self, context, storage):
        self.context = context
        self.storage = storage

    def getPortlets(self):
        """Work out which portlets to display, returning a list of dicts
        describing assignments to render.
        """
        
        pcontext = IPortletContext(self.context, None)
        if pcontext is None:
            return []
            
        # Holds a list of (category, key, assignment).
        categories = [] 
        
        # Keeps track of the blacklisting status for global categores 
        # (user, group, content type). The status is either True (blocked)
        # or False (not blocked).
        blacklisted = {}
                
        # This is the name of the manager (column) we're rendering
        manager = self.storage.__name__
        
        # 1. Fetch blacklisting status for each global category

        # First, find out which categories we will need to determine
        # blacklist status for
        
        for category, key in pcontext.globalPortletCategories(False):
            blacklisted[category] = None
        
        # Then walk the content hierarchy to find out what blacklist status
        # was assigned. Note that the blacklist is tri-state; if it's None it
        # means no assertion has been made (i.e. the category has neither been
        # whitelisted or blacklisted by this object or any parent). The first
        # item to give either a blacklisted (True) or whitelisted (False)
        # value for a given item will set the appropriate value. Parents of
        # this item that also set a black- or white-list value will then be
        # ignored.

        # Whilst walking the hierarchy, we also collect parent portlets, 
        # until we hit the first block.

        current = self.context
        currentpc = pcontext
        blacklistFetched = set()
        parentsBlocked = False
        
        while current is not None and currentpc is not None:
            assignable = ILocalPortletAssignable(current, None)
            if assignable is not None:
                annotations = IAnnotations(assignable)
                
                if not parentsBlocked:
                    local = annotations.get(CONTEXT_ASSIGNMENT_KEY, None)
                    if local is not None:
                        localManager = local.get(manager, None)
                        if localManager is not None:
                            categories.extend([(CONTEXT_CATEGORY, currentpc.uid, a) for a in localManager.values()])

                blacklistStatus = annotations.get(CONTEXT_BLACKLIST_STATUS_KEY, {}).get(manager, None)
                if blacklistStatus is not None:
                    for cat, status in blacklistStatus.items():
                        if cat == CONTEXT_CATEGORY:
                            if not parentsBlocked and status == True:
                                parentsBlocked = True
                        else: # global portlet categories
                            if blacklisted.get(cat, False) is None:
                                blacklisted[cat] = status
                            if status is not None:
                                blacklistFetched.add(cat)
                                
            # We can abort if parents are blocked and we've fetched all
            # blacklist statuses
            
            if parentsBlocked and len(blacklistFetched) == len(blacklisted):
                break
                    
            # Check the parent - if there is no parent, we will stop
            current = currentpc.getParent()
            if current is not None:
                currentpc = IPortletContext(current, None)
        
        # Get all global mappings for non-blacklisted categories
        
        for category, key in pcontext.globalPortletCategories(False):
            if not blacklisted[category]:
                mapping = self.storage.get(category, None)
                if mapping is not None:
                    for a in mapping.get(key, {}).values():
                        categories.append((category, key, a,))
        
        assignments = []
        for category, key, assignment in categories:
            assignments.append({'category'    : category,
                                'key'         : key,
                                'name'        : assignment.__name__,
                                'assignment'  : assignment
                                })
        return assignments
        
class PlacelessPortletRetriever(PortletRetriever):
    """A placeless portlet retriever.
    
    This will aggregate user portlets, then group portlets.
    """
    
    implements(IPortletRetriever)
    adapts(Interface, IPlacelessPortletManager)
    
    def __init__(self, context, storage):
        self.context = context
        self.storage = storage
        
    def getPortlets(self):
        pcontext = IPortletContext(self.context, None)
        if pcontext is None:
            return []
            
        assignments = []
        for category, key in pcontext.globalPortletCategories(True):
            mapping = self.storage.get(category, None)
            if mapping is not None:
                for assignment in mapping.get(key, {}).values():
                    assignments.append({'category'    : category,
                                        'key'         : key,
                                        'name'        : assignment.__name__,
                                        'assignment'  : assignment
                                        })
    
        return assignments
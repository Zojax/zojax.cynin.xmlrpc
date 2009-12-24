##############################################################################
#
# Copyright (c) 2009 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""

$Id$
"""
import cgi, pytz, urllib2, time
from datetime import datetime

from zope import interface, component, security
from zope.traversing.browser import absoluteURL
from zope.app.publisher.xmlrpc import MethodPublisher
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.app.component.hooks import getSite
from zope.app.intid.interfaces import IIntIds
from zope.dublincore.interfaces import IZopeDublinCore
from zope.interface.common.idatetime import ITZInfo
from zope.app.security.interfaces import IAuthentication
from zope.session.interfaces import IClientIdManager, ISession

from zojax.catalog.interfaces import ICatalog
from zojax.authentication.utils import getPrincipalByLogin, getPrincipal
from zojax.principal.profile.interfaces import IPersonalProfile
from zojax.personal.space.interfaces import IPersonalSpace
from zojax.content.discussion.catalog import getCatalog
from zojax.content.discussion.interfaces import IDiscussible, IContentDiscussion
from zojax.content.discussion.comment import Comment
from zojax.content.type.interfaces import IContentType, IPortalType

def getEmailById(principalId):
    principal = getPrincipal(principalId)
    if principal is not None:
        profile = IPersonalProfile(principal)
        return profile.email

class StackerView(MethodPublisher):

    types = ('content.blogpost', 'contenttype.image', 'contenttype.file', 'contenttype.event',
             'contenttype.document')

    def sayhello(self):
        """User authentication"""

        #We should kick off session
        component.getUtility(IClientIdManager).setRequestId(self.request, str(int(time.time()) - 1000000000) )

        if not IUnauthenticatedPrincipal.providedBy(self.request.principal):
            return "Hello"
        else:
            return ""

    def getSiteTitle(self):
        """Return the site title"""
        return getSite().title

    def getSiteLogo(self):
        return '%s/@@/logo.png' % absoluteURL(getSite(), self.request)

    def getStatusMessage(self,username=''):
        """Returns current status message of passed user."""
        return "Under development"

    def getUserInfo(self, loginOrId):
        """Return the user name details, and avatar url for given userid"""

        principal = getPrincipal(loginOrId)
        if principal is None:
            principal = getPrincipalByLogin(loginOrId)

        if principal is not None:
            profile = IPersonalProfile(principal, None)
            homeFolder = IPersonalSpace(principal, None)
            profileUrl = homeFolder is not None and '%s/profile/'%absoluteURL(homeFolder, self.request) or ''

            if profile.avatar is not None:
                iconURL = '%s/profile.avatar/%s' % (absoluteURL(getSite(), self.request), principal.id)
            else:
                iconURL = '%sprofileImage' % profileUrl

            return {'username' : loginOrId,
                    'fullname' : principal.title,
                    'email' : profile.email,
                    'home_page' : profileUrl,
                    'location' : profileUrl,
                    'description' : principal.description,
                    'portrait_url' : iconURL
                    }
        else:
            raise ValueError("User %s Does not Exist!" % loginOrId)

    def getRecentUpdates(self, maxitemcount=5, pagenumber=1):
        """Return the recent updates, up to a maximum of maxitemcount items will be returned in a list"""
        query = dict(sort_order='reverse', sort_on='modified',
                     searchContext=(getSite(),), isDraft={'any_of': (False,)},
                     type={'any_of': self.types}
                     )

        items, fullLength = self._search(query, maxitemcount, pagenumber)
        outlist = [self._setItem(item) for item in items]
        return {'itemcount':fullLength,'itemlist':outlist}

    def _setItem(self, item):
        lastDate, obj, commentCount, action, lastAuthor = item
        dc = IZopeDublinCore(obj)
        ids = component.getUtility(IIntIds, context = self.context)
        return {
                'id': obj.__name__,
                'itemuid': ids.getId(obj),
                'title': dc.title,
                'description': dc.description,
                'portal_type': IContentType(obj).name,
                'created': dc.created,
                'modified': lastDate,
                'creator': getEmailById(dc.creators[0]) or dc.creators[0],
                'allowedcomments': IDiscussible.providedBy(obj),
                'commentcount': commentCount,
                'absoluteurl': absoluteURL(obj, self.request),
                'cancomment': IDiscussible.providedBy(obj),
                'lastchangedate': lastDate,
                'lastchangeaction': action,
                'lastchangeperformer': getEmailById(lastAuthor) or lastAuthor,
                'canedit': security.checkPermission('zojax.ModifyContent', obj) ,
                }

    def getTypeInfo(self, typeName):
        """Returns the type title and icon url for given typename"""
        ct = component.queryUtility(IContentType, name = typeName, context = self.context)
        if ct is not None:
            iconURL = component.getMultiAdapter((ct, self.request), name = 'zmi_icon' ).url()
            iconURL = iconURL.replace('@', '%40')
            return {'typename': ct.name,
                    'typetitle': unicode(ct.title),
                    'typeiconurl': iconURL,
                    }
        else:
            raise ValueError("Portal type %s Does not Exist!" % typeName)

    def search(self, searchableText='', maxitemcount=5, pagenumber=1):
        """Returns result for search text entered for recent user"""
        query = dict(sort_order='reverse', sort_on='modified',
                     searchContext=(getSite(),), isDraft={'any_of': (False,)},
                     type={'any_of': self.types}, searchableText = searchableText,
                     )

        items, fullLength = self._search(query, maxitemcount, pagenumber)
        outlist = [self._setSearchResultItem(item) for item in items]
        return {'itemcount':fullLength,'itemlist':outlist,'term':searchableText}

    def _search(self, query, maxitemcount, pagenumber):
        catalog = component.queryUtility(ICatalog, context = self.context)
        discussCatalog = getCatalog()
        if catalog is not None:
            items = []
            for obj in catalog.searchResults(**query):
                dc = IZopeDublinCore(obj)

                comments = discussCatalog.search(content = obj)
                commentsCount = len(comments)
                if commentsCount:
                    lastComment = comments.__iter__().next()
                    lastDate = max(lastComment.date, dc.modified)
                    action = 'commented'
                    lastAuthor = lastComment.author
                else:
                    action = 'modified'
                    lastAuthor = dc.creators[-1]
                    lastDate = dc.modified

                items.append((lastDate, obj, commentsCount, action, lastAuthor))

            indFrom = (maxitemcount * pagenumber) - maxitemcount
            indTo = maxitemcount * pagenumber
            items.sort(reverse=True)
            fullLength = len(items)
            items = items[indFrom:indTo]

            return items, fullLength

    def _setSearchResultItem(self, item):
        lastDate, obj, commentCount, action, lastAuthor = item
        dc = IZopeDublinCore(obj)
        ids = component.getUtility(IIntIds, context = self.context)

        return {
                'id': obj.__name__,
                'itemuid': ids.getId(obj),
                'title': dc.title,
                'portal_type': IContentType(obj).name,
                'modified': lastDate,
                'creator': getEmailById(dc.creators[0]) or dc.creators[0],
                'absoluteurl': absoluteURL(obj, self.request),
                'relevance': 100, #TODO
                }

    def getComments(self, uid):
        """Return all the comments for the given object's UID"""
        ids = component.getUtility(IIntIds, context = self.context)
        obj = ids.getObject(int(uid))

        discussCatalog = getCatalog()
        return [{'depth':0,
                 'title':'',
                 'commenter': getEmailById(comment.author) or comment.author,
                 'commenttext':comment.comment,
                 'modified':comment.date,
                 'id':comment.__name__,
                 }
                for comment in discussCatalog.search(content = obj)]

    def addNewComment(self, uid, commentTitle, commentBody, commentId = None):
        """Adds a comment on the provided UID with given title, text and commenter user.
        """
        ids = component.getUtility(IIntIds, context = self.context)
        obj = ids.getObject(int(uid))
        discussion = IContentDiscussion(obj)

        commentText = cgi.escape(commentBody)

        comment = Comment(self.request.principal.id, commentText)

        tz = ITZInfo(self.request, None)
        if tz:
            comment.date = datetime.now(tz)
        else:
            comment.date = datetime.now(pytz.utc)

        comment = discussion.add(comment)

        return uid

    def getBlogEntry(self, uid):
        """Return the info available for a Blog Entry"""
        ids = component.getUtility(IIntIds, context = self.context)
        post = ids.getObject(int(uid))
        return {'htmlbody' : post.text.cooked}

    def getFileInfo(self,uid):
        """Return the info available for a file"""
        ids = component.getUtility(IIntIds, context = self.context)
        file = ids.getObject(int(uid))

        return {'filename': file.data.filename,
                'fileformat': file.data.mimeType,
                'filesize': file.data.size,
                }

    def getEventInfo(self,uid):
        """Return the information available for a Calendar Event"""
        ids = component.getUtility(IIntIds, context = self.context)
        event = ids.getObject(int(uid))

        return {'start':event.startDate,'end':event.endDate,
                'location':event.location,'contactName':event.contactName,
                'contactEmail':event.contactEmail,'contactPhone':event.contactPhone,
                'attendees':event.attendees,'bodyhtml': event.text.cooked
                }

    def getWikiBody(self,uid):
        """Return the wiki body text, pre-cooked and processed"""
        ids = component.getUtility(IIntIds, context = self.context)
        page = ids.getObject(int(uid))

        return page.text.cooked

##############################################################################
#
# Copyright (c) 2007 Zope Foundation and Contributors.
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
""" zojax.principal.profile tests

$Id$
"""
import os, unittest, doctest
from zope.app.testing import functional
from zope.app.component.hooks import setSite
from zope.app.rotterdam import Rotterdam
from zojax.layoutform.interfaces import ILayoutFormLayer


zojaxContentXMLRPCLayer = functional.ZCMLLayer(
    os.path.join(os.path.split(__file__)[0], 'ftesting.zcml'),
    __name__, 'zojaxContentXMLRPCLayer', allow_teardown=True)


def FunctionalDocFileSuite(*paths, **kw):
    layer = zojaxContentXMLRPCLayer

    kw['package'] = doctest._normalize_module(kw.get('package'))

    kwsetUp = kw.get('setUp')
    def setUp(test):
        functional.FunctionalTestSetup().setUp()
        root = functional.getRootFolder()
        setSite(root)
        setattr(root, 'title', 'Test Site')

    kw['setUp'] = setUp

    kwtearDown = kw.get('tearDown')
    def tearDown(test):
        setSite(None)
        functional.FunctionalTestSetup().tearDown()

    kw['tearDown'] = tearDown

    if 'optionflags' not in kw:
        old = doctest.set_unittest_reportflags(0)
        doctest.set_unittest_reportflags(old)
        kw['optionflags'] = (old|doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE)

    suite = doctest.DocFileSuite(*paths, **kw)
    suite.layer = layer
    return suite


class IDefaultSkin(ILayoutFormLayer, Rotterdam):
    """ skin """


def test_suite():
    return unittest.TestSuite((
            FunctionalDocFileSuite("testbrowser.txt"),
            ))

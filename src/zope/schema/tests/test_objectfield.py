##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
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
"""This set of tests exercises Object fields.

$Id$
"""
from unittest import TestSuite, main, makeSuite

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Attribute, Interface, implements
from zope.schema import Object, TextLine
from zope.schema.fieldproperty import FieldProperty
from zope.schema.interfaces import ValidationError
from zope.schema.interfaces import RequiredMissing, WrongContainedType
from zope.schema.interfaces import WrongType, SchemaNotFullyImplemented
from zope.schema.tests.test_field import FieldTestBase

_ = MessageIDFactory('zope')


class ITestSchema(Interface):
    """A test schema"""
    
    foo = TextLine(
        title=_(u"Foo"),
        description=_(u"Foo description"),
        default=u"",
        required=True)
        
    bar = TextLine(
        title=_(u"Bar"),
        description=_(u"Bar description"),
        default=u"",
        required=False)
        
    attribute = Attribute("Test attribute, an attribute can't be validated.")
    

class TestClass(object):
    
    implements(ITestSchema)
    
    _foo = u''
    _bar = u''
    _attribute = u''
       
    def getfoo(self):
        return self._foo 
        
    def setfoo(self, value):
        self._foo = value
        
    foo = property(getfoo, setfoo, None, u'foo')
    
    def getbar(self):
        return self._bar 
        
    def setbar(self, value):
        self._bar = value
        
    bar = property(getbar, setbar, None, u'foo')
    
    def getattribute(self):
        return self._attribute 
        
    def setattribute(self, value):
        self._attribute = value
        
    attribute = property(getattribute, setattribute, None, u'attribute')


class FieldPropertyTestClass(object):
    
    implements(ITestSchema)
    
    
    foo = FieldProperty(ITestSchema['foo'])
    bar = FieldProperty(ITestSchema['bar'])
    attribute = FieldProperty(ITestSchema['attribute'])
   

class NotFullyImplementedTestClass(object):
    
    implements(ITestSchema)
    
    foo = FieldProperty(ITestSchema['foo'])
    # bar = FieldProperty(ITestSchema['bar']): bar is not implemented
    # attribute
    
    
class ObjectTest(FieldTestBase):
    """Test the Object Field."""
    def getErrors(self, f, *args, **kw):
        try:
            f(*args, **kw)
        except WrongContainedType, e:
            try:
                return e[0]
            except:  
                return []
        self.fail('Expected WrongContainedType Error')    
    
    def makeTestObject(self, **kw):
        kw['schema'] = kw.get('schema', Interface)
        return Object(**kw)

    _Field_Factory = makeTestObject
            
    def makeTestData(self):
        return TestClass()

    def makeFieldPropertyTestClass(self):
        return FieldPropertyTestClass()
                
    def makeNotFullyImplementedTestData(self):
        return NotFullyImplementedTestClass()
        
    def invalidSchemas(self):
        return ['foo', 1, 0, {}, [], None]
        
    def validSchemas(self):
        return [Interface, ITestSchema]
                               
    def test_init(self):
        for schema in self.validSchemas():
            field = Object(schema=schema)
        for schema in self.invalidSchemas():
            self.assertRaises(ValidationError, Object, schema=schema)
            self.assertRaises(WrongType, Object, schema=schema)
            
    def testValidate(self):
        # this test of the base class is not applicable
        pass

    def testValidateRequired(self):
        # this test of the base class is not applicable
        pass
        
    def test_validate_required(self):
        field = self._Field_Factory(
            title=u'Required field', description=u'',
            readonly=False, required=True)
        self.assertRaises(RequiredMissing, field.validate, None)
        
    def test_validate_TestData(self):
        field = self.makeTestObject(schema=ITestSchema, required=False)
        data = self.makeTestData()
        field.validate(data)
        field = self.makeTestObject(schema=ITestSchema)
        field.validate(data)
        data.foo = None
        self.assertRaises(ValidationError, field.validate, data)
        self.assertRaises(WrongContainedType, field.validate, data)
        errors = self.getErrors(field.validate, data)
        self.assertEquals(errors[0], RequiredMissing())

    def test_validate_FieldPropertyTestData(self):
        field = self.makeTestObject(schema=ITestSchema, required=False)
        data = self.makeFieldPropertyTestClass()
        field.validate(data)
        field = self.makeTestObject(schema=ITestSchema)
        field.validate(data)
        self.assertRaises(ValidationError, setattr, data, 'foo', None)
        self.assertRaises(RequiredMissing, setattr, data, 'foo', None)
        
    def test_validate_NotFullyImplementedTestData(self):
        field = self.makeTestObject(schema=ITestSchema, required=False)
        data = self.makeNotFullyImplementedTestData()
        self.assertRaises(ValidationError, field.validate, data)
        self.assertRaises(WrongContainedType, field.validate, data)
        errors = self.getErrors(field.validate, data)
        self.assertEquals(errors[0], SchemaNotFullyImplemented())

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(ObjectTest))
    return suite

if __name__ == '__main__':
    main(defaultTest='test_suite')

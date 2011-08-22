# -*- coding: utf-8 -*-
from __future__ import with_statement
from django.contrib.auth.models import User, AnonymousUser
from django.test.testcases import TestCase
from django.utils.importlib import import_attribute, iter_import_attributes
    

class LoadTests(TestCase):
        
    def test_import_attribute(self):
        obj = import_attribute('django.contrib.auth.models.User')
        self.assertEqual(obj, User)
        
    def test_import_attribute_fail_type(self):
        self.assertRaises(TypeError, import_attribute, 'notanimportpath')
        
    def test_import_attribute_fail_import(self):
        self.assertRaises(ImportError, import_attribute,
                          'django.contrib.auth.not_models.User')
        
    def test_import_attribute_fail_attribute(self):
        self.assertRaises(AttributeError, import_attribute,
                          'django.contrib.auth.models.NotAUser')
        
    def test_import_attribute_exception_handler(self):
        class MyException(Exception): pass
        def exc_handler(*args, **kwargs):
            raise MyException
        self.assertRaises(MyException, import_attribute,
                          'django.contrib.auth.models.NotAUser', exc_handler)
        self.assertRaises(MyException, import_attribute,
                          'django.contrib.auth.not_models.User', exc_handler)
        self.assertRaises(TypeError, import_attribute, 'notanimportpath')

    def test_iter_import_attributes(self):
        import_paths = ['django.contrib.auth.models.User',
                        'django.contrib.auth.models.AnonymousUser']
        objs = list(iter_import_attributes(import_paths))
        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0], User)
        self.assertEqual(objs[1], AnonymousUser)
        
    def test_iter_import_attributes_propagates_exception_handler(self):
        class MyException(Exception): pass
        def exc_handler(*args, **kwargs):
            raise MyException
        gen = iter_import_attributes(['django.contrib.auth.models.User',
                                      'django.contrib.auth.models.NotAUser'],
                                      exc_handler)
        user = gen.next()
        self.assertEqual(user, User)
        self.assertRaises(MyException, gen.next)
    
    def test_iter_import_attributes_ignore_exceptions(self):
        def exc_handler(*args, **kwargs):
            pass

        import_paths = ['django.contrib.auth.models.User',
                        'django.contrib.auth.models.NotAUser',
                        'django.contrib.auth.models.AnonymousUser']
        objs = list(iter_import_attributes(import_paths, exc_handler))
        self.assertEqual(len(objs), 2)
        self.assertEqual(objs[0], User)
        self.assertEqual(objs[1], AnonymousUser)

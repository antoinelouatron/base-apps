# -*- coding: utf-8 -*-
import os.path

import django.db.models as models
from django.core.files.uploadedfile import InMemoryUploadedFile
import django.core.exceptions as excs
import django.forms as forms
from django.views import View

from bulkimport.forms.importfile import FileImportForm, is_m2m 
from bulkimport import dict_utils
from bulkimport.forms import fields as bf
from bulkimport import importers
from dev import test_view
from dev.test_utils import TestCase
import users.models as um

class DummyModel(models.Model):

    class Meta:
        app_label = "bulkimport"

    field1 = models.IntegerField()
    field2 = models.CharField(max_length=64)
    field3 = models.CharField(max_length=64)

class Test(FileImportForm):
    class Meta:
        model = DummyModel
        fields = ['field1']
        name_fields = ['field2', 'field3']


class DummyForm(forms.ModelForm):
    class Meta:
        model = DummyModel
        fields = ['field2', 'field3']

    def clean_field2(self):
        import hashlib
        val = self.cleaned_data['field2']
        return hashlib.md5(val.encode()).hexdigest()


class Test2(FileImportForm):
    class Meta:
        model = DummyModel
        # fields = ['field1']
        name_fields = ['field2', 'field3']
        form = DummyForm

class TestForm(TestCase):

    def test_form_creation(self):
        # make sure metaclass magic doesn't throw Exception
        Test()
        with self.assertRaises(excs.ImproperlyConfigured):
            class Test5(FileImportForm):
                class Meta:
                    model = DummyModel
                    fields = ['field1']
        with self.assertRaises(excs.ImproperlyConfigured):
            class Test4(FileImportForm):
                class Meta:
                    fields = ['field1']
                    name_fields = ['field1']

    def test_name_mapping(self):
        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'test_file.json')
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.json',
                'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertTrue(t.is_valid())
            instances = t.save(commit=False)
            for inst in instances:
                self.assertTrue(isinstance(inst, DummyModel))
                self.assertTrue(inst.pk is None)
                self.assertTrue(isinstance(inst.field1, int))
                self.assertTrue(isinstance(inst.field2, str))
                self.assertTrue(isinstance(inst.field3, str))
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.json',
                'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f4',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertFalse(t.is_valid())

    def test_atomic_form(self):
        self.assertEqual(Test2.atomic_form, DummyForm)
        path = os.path.join(os.path.dirname(__file__), "fixtures", "test_file.json")
        with open(path, 'rb') as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "test_file.json",
                "text/plain", os.path.getsize(path), "utf-8"
            )}
            t = Test2({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertTrue(t.is_valid())
            instances = t.save_all(commit=False)
            for inst in instances:
                self.assertEqual(len(inst.field2), 32)
                # make sure main form value is set, even if data is passed in file
                self.assertEqual(inst.field1, 1)

    def test_csv(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "test_file.csv")
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.csv', 'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertTrue(t.is_valid())
            # test csv data formatter here
            self.assertIsNotNone(t._data_formatter)
            for form, _ in t._forms:
                res = t._data_formatter(form._generated_data)
                self.assertIn('field3', res)
                self.assertIn('field2', res)
    
    def test_errors(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "test_file.dum")
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.dum', 'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertFalse(t.is_valid())
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.json', 'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertFalse(t.is_valid())
        path = os.path.join(os.path.dirname(__file__), "fixtures", "test_file.json")
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.json', 'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f2',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertFalse(t.is_valid())
            with self.assertRaises(forms.ValidationError):
                t.save_all()
        path = os.path.join(os.path.dirname(__file__), "fixtures", "test_file2.json")
        with open(path, 'rb') as upl_file:
            upl_dict = {'import_file': InMemoryUploadedFile(
                upl_file, None, 'test_file.json', 'text/plain', os.path.getsize(path),
                'utf-8')}
            t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f2',
                    '_encoding': 'utf8'}, upl_dict)
            self.assertFalse(t.is_valid())
            with self.assertRaises(forms.ValidationError):
                t.save_all()
        t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'})
        self.assertFalse(t.is_valid())
    
    def test_types(self):
        t = Test({'field1': '1', '_name_mapping_0': 'f2', '_name_mapping_1': 'f3',
                    '_encoding': 'utf8'})
        f1, f2 = t.import_fields
        # we get BoundField
        self.assertIsInstance(f1.field, forms.ChoiceField)
        self.assertIsInstance(f2.field, bf.NameMappingField)
    
    def test_is_m2m(self):
        self.assertFalse(is_m2m(Test, 'field1'))
        self.assertFalse(is_m2m(Test, 'field2'))
        self.assertFalse(is_m2m(Test, 'field3'))
        self.assertFalse(is_m2m(Test, '_name_mapping_0'))
        self.assertFalse(is_m2m(Test, '_name_mapping_1'))
        self.assertFalse(is_m2m(Test, '_encoding'))
        # non existent name
        self.assertFalse(is_m2m(Test, 'non_existent_field'))

class TestUtils(TestCase):

    def test_bijection(self):
        d = {"a": 1, "b": 2}
        self.assertFalse(dict_utils.is_bijection(d, "ab", (1,1)))
        self.assertFalse(dict_utils.is_bijection(d, "ab", (1,3)))
        self.assertFalse(dict_utils.is_bijection(d, "ac", (1,3)))
        self.assertFalse(dict_utils.is_bijection(d, "ac", (1,2)))
        self.assertTrue(dict_utils.is_bijection(d, "ab", (1,2)))
        self.assertFalse(dict_utils.is_bijection(d, "a", (1,2)))
        self.assertFalse(dict_utils.is_bijection(d, "ab", (1,2,3)))
    
    def test_injection(self):
        d = {'a': 1, 'b': 2}
        self.assertFalse(dict_utils.is_injection(d, "ab", (1,1)))
        self.assertFalse(dict_utils.is_injection(d, "ab", (1,3)))
        self.assertFalse(dict_utils.is_injection(d, "ac", (1,3)))
        self.assertFalse(dict_utils.is_injection(d, "ac", (1,2)))
        self.assertTrue(dict_utils.is_injection(d, "ab", (1,2)))
        self.assertTrue(dict_utils.is_injection(d, "ab", (1,2, 3)))
        self.assertFalse(dict_utils.is_injection(d, "abc", (1,2,3)))
    

#fileimport

class TestFileImport(TestCase):
    
    def test_uniqueness(self):
        importers.register("name", "name", View)
        with self.assertRaises(ValueError):
            importers.register("name", "name2", View)
        importers.unregister("name")
        with self.assertRaises(ValueError):
            importers.unregister("name")
    
    def test_index_access(self):
        url = test_view.TestURL(self, "import", "index", status=403)
        url.test()
        teach = um.User.objects.create_teacher(username="teach")
        url.set_user(teach)
        url.test() # only staff, no teachers
        url.status = 200
        teach.is_staff = True
        teach.save()
        url.set_user(teach)
        url.test()
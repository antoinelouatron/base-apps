# -*- coding: utf-8 -*-
import os.path

import django.db.models as models
from django.core.files.uploadedfile import InMemoryUploadedFile
import django.core.exceptions as excs
import django.forms as forms
from django.views import View

from django.core.files.uploadedfile import SimpleUploadedFile

from bulkimport.forms.importfile import FileImportForm, is_m2m 
from bulkimport import dict_utils
from bulkimport.forms import fields as bf
from bulkimport import importers
from dev.test_utils import TestCase

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
    

class OptionalForm(forms.ModelForm):
    """
    field3 est facultatif : sa colonne peut manquer du fichier.
    """

    class Meta:
        model = DummyModel
        fields = ["field2", "field3"]

    field3 = forms.CharField(required=False)


class TestOptional(FileImportForm):
    class Meta:
        model = DummyModel
        fields = ["field1"]
        name_fields = ["field2", "field3"]
        form = OptionalForm


class TestImportErrors(TestCase):
    """
    Un fichier qui ne colle pas doit produire un message exploitable, jamais
    une 500 ni trois cents lignes de bruit.
    """

    def build(self, content, name="donnees.csv", form_class=None,
              mapping=("f2", "f3"), encoding="utf8"):
        if isinstance(content, str):
            content = content.encode("utf-8")
        upl = {"import_file": SimpleUploadedFile(name, content)}
        data = {"field1": "1", "_encoding": encoding}
        for i, col in enumerate(mapping):
            data["_name_mapping_%d" % i] = col
        return (form_class or Test)(data, upl)

    def codes(self, form):
        """
        Codes des erreurs, tous champs confondus.
        """
        found = []
        for messages in form.errors.get_json_data().values():
            found.extend(m["code"] for m in messages)
        return found

    def test_empty_file(self):
        # Django refuse le fichier de taille nulle avant même la conversion
        t = self.build("")
        self.assertFalse(t.is_valid())
        self.assertIn("empty", self.codes(t))

    def test_blank_file(self):
        # un fichier qui n'a que des blancs atteint le convertisseur : le
        # calcul du séparateur y partait en UnboundLocalError, donc en 500
        t = self.build("\n   \n")
        self.assertFalse(t.is_valid())
        self.assertIn("empty_file", self.codes(t))

    def test_header_only(self):
        # créait zéro objet en annonçant « Importation réussie »
        t = self.build("f2,f3\n")
        self.assertFalse(t.is_valid())
        self.assertIn("no_data", self.codes(t))
        self.assertEqual(t.import_report.total_rows, 0)

    def test_no_header(self):
        t = self.build(",,\n1,2,3\n")
        self.assertFalse(t.is_valid())
        self.assertIn("no_header", self.codes(t))

    def test_bad_encoding(self):
        t = self.build("f2,f3\néa,àb\n".encode("latin-1"))
        self.assertFalse(t.is_valid())
        self.assertIn("bad_encoding", self.codes(t))
        self.assertIn("latin_1", str(t.errors))

    def test_upper_case_extension(self):
        # DONNEES.CSV arrive tel quel depuis Windows
        t = self.build("f2,f3\na,b\n", name="DONNEES.CSV")
        self.assertTrue(t.is_valid(), t.errors.as_text())

    def test_spreadsheet_extension(self):
        t = self.build("nimporte", name="colloscope.xlsx")
        self.assertFalse(t.is_valid())
        self.assertIn("bad_extension", self.codes(t))
        text = t.errors.as_text()
        self.assertIn(".xlsx", text)
        self.assertIn("CSV", text)

    def test_unknown_extension_names_the_extension(self):
        # citait le nom du fichier au lieu de son extension
        t = self.build("nimporte", name="colloscope.txt")
        self.assertFalse(t.is_valid())
        self.assertIn(".txt", t.errors.as_text())

    def test_no_extension(self):
        t = self.build("f2,f3\na,b\n", name="colloscope")
        self.assertFalse(t.is_valid())
        self.assertIn("bad_extension", self.codes(t))

    def test_bad_json(self):
        t = self.build('[{"f2": 1, ', name="donnees.json")
        self.assertFalse(t.is_valid())
        self.assertIn("bad_content", self.codes(t))
        # la position d'origine est conservée
        self.assertIn("ligne 1", t.errors.as_text())

    def test_json_single_object(self):
        t = self.build('{"f2": 1, "f3": 2}', name="donnees.json")
        self.assertFalse(t.is_valid())
        self.assertIn("bad_format", self.codes(t))

    def test_missing_column_reported_once(self):
        # une colonne mal nommée produisait une erreur par ligne
        content = "f2,fX\n" + "".join("a%d,b%d\n" % (i, i) for i in range(40))
        t = self.build(content)
        self.assertFalse(t.is_valid())
        self.assertIn("missing_columns", self.codes(t))
        self.assertEqual(t.import_report.missing_columns, ["f3"])
        self.assertEqual(len(t.errors.get_json_data()["__all__"]), 1)
        text = t.errors.as_text()
        self.assertIn("f3", text)
        self.assertIn("fX", text)

    def test_optional_column_may_be_missing(self):
        # civilite, salle : leur absence n'a pas à condamner l'import
        t = self.build("f2\na\nb\n", form_class=TestOptional)
        self.assertTrue(t.is_valid(), t.errors.as_text())

    def test_single_column_hints_at_delimiter(self):
        t = self.build("f2|f3\na|b\n")
        self.assertFalse(t.is_valid())
        self.assertIn("séparateur", t.errors.as_text())

    def test_line_numbers(self):
        # ligne 1 = en-tête, la 2e ligne de données est donc la ligne 3
        t = self.build("f2,f3\na,b\n,d\nc,e\n")
        self.assertFalse(t.is_valid())
        report = t.import_report
        self.assertEqual(report.total_rows, 3)
        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.rows[0].location, "ligne 3")

    def test_error_cap(self):
        content = "f2,f3\n" + "".join(",b%d\n" % i for i in range(40))
        t = self.build(content)
        self.assertFalse(t.is_valid())
        report = t.import_report
        self.assertEqual(report.error_count, 40)
        self.assertEqual(len(report.rows), t.MAX_REPORTED_ROWS)
        self.assertEqual(report.hidden_count, 40 - t.MAX_REPORTED_ROWS)
        # un seul message porté par le champ, pas quarante
        self.assertEqual(len(t.errors.get_json_data()["import_file"]), 1)

    def test_json_positions(self):
        content = '[{"f2": "a", "f3": "b"}, {"f2": "", "f3": "d"}, {"f2": "e", "f3": "f"}]'
        t = self.build(content, name="donnees.json")
        self.assertFalse(t.is_valid())
        self.assertEqual(t.import_report.rows[0].location, "objet 2")

    def test_extra_values(self):
        # une cellule contenant une virgule décale toute la ligne, en silence
        t = self.build("f2,f3\na,b,c\n")
        self.assertFalse(t.is_valid())
        report = t.import_report
        self.assertEqual(report.error_count, 1)
        self.assertIn("plus de valeurs que de colonnes",
                      report.rows[0].errors[0][1][0])

    def test_bom_in_header(self):
        # Excel écrit un BOM : la première colonne devenait introuvable
        t = self.build("\ufefff2,f3\na,b\n".encode("utf-8"))
        self.assertTrue(t.is_valid(), t.errors.as_text())

    def test_row_errors_are_labelled_by_file_column(self):
        # l'utilisateur cherche « f2 » dans son fichier, pas « field2 »
        t = self.build("f2,f3\n,b\n")
        self.assertFalse(t.is_valid())
        labels = [label for label, _msgs in t.import_report.rows[0].errors]
        self.assertIn("f2", labels)


class TestRow(TestCase):

    def test_row_is_a_dict(self):
        row = dict_utils.Row({"a": 1}, line_no=12)
        self.assertIsInstance(row, dict)
        self.assertEqual(row["a"], 1)
        self.assertEqual(dict_utils.line_of(row), 12)

    def test_line_of_tolerates_plain_dict(self):
        self.assertIsNone(dict_utils.line_of({"a": 1}))

    def test_row_survives_map_keys(self):
        row = dict_utils.Row({"a": 1}, line_no=3)
        out = dict_utils.map_keys(row, {"a": "b"})
        self.assertEqual(dict_utils.line_of(out), 3)
        self.assertEqual(out["b"], 1)

    def test_format_row_skips_empty_values(self):
        text = dict_utils.format_row({"a": 1, "b": "", "c": None, "d": "x"})
        self.assertIn("a=1", text)
        self.assertIn("d=x", text)
        self.assertNotIn("b=", text)
        self.assertNotIn("c=", text)

    def test_format_row_truncates(self):
        text = dict_utils.format_row({"a": "x" * 200})
        self.assertLess(len(text), 100)
        self.assertIn("...", text)

    def test_locate(self):
        seq = dict_utils.DictIterable([], [], position_label="objet")
        self.assertEqual(seq.locate(dict_utils.Row({}, line_no=4)), "objet 4")
        self.assertEqual(seq.locate({}), "")

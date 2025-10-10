from unittest import TestSuite, TextTestResult, TextTestRunner
from unittest.case import TestCase
from unittest.result import TestResult
from django.test import TestCase as BasetestCase, runner

class AssertCountResult(TextTestResult):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assert_count = 0

class CustomRunner(TextTestRunner):

    resultclass = AssertCountResult

    def run(self, test: TestSuite | TestCase) -> TestResult:
        res = super().run(test)
        if isinstance(res, AssertCountResult):
            self.stream.write(f"{res.assert_count} assertions.\n")
        return res

class DjangoRunner(runner.DiscoverRunner):
    
    test_runner = CustomRunner

class TestCase(BasetestCase):

    # @classmethod
    # def setUpClass(cls) -> None:
    #     cls.__assert_count = 0
    #     return super().setUpClass()

    def __getattribute__(self, name):
        if name.startswith("assert"):
            self.__class__.__assert_count += 1
        return object.__getattribute__(self, name)
    
    def run(self, result=None):
        self.__class__.__assert_count = 0
        res = super().run(result=result)
        if isinstance(res, AssertCountResult):
            res.assert_count += self.__class__.__assert_count
        return res

#TestCase = BasetestCase
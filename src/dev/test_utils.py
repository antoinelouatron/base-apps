from unittest import TestSuite, TextTestResult, TextTestRunner
from unittest.case import TestCase
from unittest.result import TestResult
from django.test import TestCase as BasetestCase, runner

# Nom de l'evenement qui porte le compteur d'un worker vers le processus
# parent. ParallelTestSuite.handle_event appelle la methode de meme nom sur le
# resultat parent, c'est le seul canal disponible entre les deux processus.
ASSERT_COUNT_EVENT = "addAssertCount"

class AssertCountResult(TextTestResult):
    """Resultat cote parent : totalise les assertions de tous les tests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assert_count = 0

    def addAssertCount(self, test, count):
        self.assert_count += count

class RemoteAssertCountResult(runner.RemoteTestResult):
    """Resultat cote worker : le compteur part dans la file des evenements."""

    def addAssertCount(self, test, count):
        self.events.append((ASSERT_COUNT_EVENT, self.test_index, count))

class RemoteAssertCountRunner(runner.RemoteTestRunner):

    resultclass = RemoteAssertCountResult

class AssertCountParallelSuite(runner.ParallelTestSuite):

    runner_class = RemoteAssertCountRunner

class CustomRunner(TextTestRunner):

    resultclass = AssertCountResult

    def run(self, test: TestSuite | TestCase) -> TestResult:
        res = super().run(test)
        # Absent si --pdb ou --debug-sql imposent leur propre resultclass.
        count = getattr(res, "assert_count", None)
        if count is not None:
            self.stream.write(f"{count} assertions.\n")
        return res

class DjangoRunner(runner.DiscoverRunner):

    test_runner = CustomRunner
    parallel_test_suite = AssertCountParallelSuite

class AssertCountMixin:
    """Compte les acces aux methodes `assert*` et les remonte au resultat.

    A melanger devant n'importe quelle classe de test : les tests navigateur
    derivent de StaticLiveServerTestCase, pas du TestCase ci-dessous.
    """

    def __getattribute__(self, name):
        if name.startswith("assert"):
            self.__class__.__assert_count += 1
        return object.__getattribute__(self, name)

    def run(self, result=None):
        self.__class__.__assert_count = 0
        res = super().run(result=result)
        # Duck typing : le resultat est local ou distant selon --parallel.
        report = getattr(res, ASSERT_COUNT_EVENT, None)
        if report is not None:
            report(self, self.__class__.__assert_count)
        return res

class TestCase(AssertCountMixin, BasetestCase):
    pass

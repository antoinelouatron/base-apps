"""
Created on Mon Feb  1 14:09:22 2016
"""

import os.path

from django.contrib.auth.models import Permission
from django import urls
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import TestCase

from utils.views import json_utils, static_assets

class CheckNs():
    """
    Callable for checking existence of popns context variable.
    Opitionnaly check for presence of elements of popns list
    """

    def __init__(self, *props, msg=""):
        """
        props is a list of namespace names
        """
        self.props = props
        self.msg = msg

    def __call__(self, resp):
        if "popns" not in resp.context:
            self.msg += "Missing namespace"
            return False
        popns = resp.context["popns"]
        if not isinstance(popns, static_assets.NsData):
            self.msg = "Namespace object is not compatible."
            return False
        if len(popns) == 0:
            self.msg = "Empty js namepace."
            return len(self.props) == 0
        nsnames, values = zip(*popns.items())
        names = set(nsnames)
        for s in nsnames:
            parts = s.split(".")
            for i in range(len(parts) - 1):
                names.add(".".join(parts[:i + 1]))
        for prop in self.props:
            if prop not in names:
                self.msg += " {} name missing for request {}".format(prop, resp.request)
                self.msg += "\n Noms présents : {}".format(names)
                return False
        return True


def construct_file(fpath, content_type="text/plain"):
    """
    Construct an ImMemoryUploadedFile
    """
    upl_file = open(fpath, "rb")
    return InMemoryUploadedFile(
        upl_file,
        None,
        os.path.basename(fpath),
        content_type,
        os.path.getsize(fpath),
        "utf-8"
    )


class TestURL():

    def __init__(self, testcase: TestCase, namespace: str, name: str, **kwargs):
        """
        Reverse an url in given namespace (pass "" to skip namespace).

        possible kwargs are : status (HTML code), perm (permission codename),
        user (a YearUser to login), method (get or post), data (HTML form data),
        msg (testmethod message for tests)
        tests kwarg is a list of function taking response object and returning a boolean
        """
        self._testcase = testcase
        self._client = testcase.client
        self.set_url(namespace, name, kwargs.get("kwargs", {}))
        self._status = kwargs.get("status", 200)
        self.require_perm = kwargs.get("perm", False)
        self.user = kwargs.get("user", None)
        self.method = kwargs.get("method", "get")
        self.tests = kwargs.get("tests", [])
        self.data = kwargs.get("data", {})
        self.msg = kwargs.get("msg", "statut " + self.url)
        self._ajax = False

    def set_url(self, namespace, name, kwargs={}):
        reverse = namespace + ':' + name if namespace != "" else name
        self.url = urls.reverse(reverse, kwargs=kwargs)
        self.msg = kwargs.get("msg", "statut " + self.url)

    def set_user(self, user):
        self.user = user

    # to ease override in child class
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    def test(self, skip_title=False, **request_kwargs):
        """
        Use client to make a request to comptuted url.
        Check that permission (if any) is required, and executes any tests given at initialization.

        special kwargs
        """
        client = self._client
        testcase = self._testcase
        client.logout()
        if "cookies" in request_kwargs:
            client.cookies.load(request_kwargs.pop("cookies"))
        if self.method == "get":
            fetch = client.get
        elif self.method == "post":
            fetch = client.post
        elif self.method == "head":
            fetch = client.head
        elif self.method == "put":
            fetch = client.put
        else:
            testcase.fail("Méthode inconnue " + self.method)
        if self.require_perm:
            if self.user is None:
                testcase.fail("Aucun utilisateur donnée pour " + self.url)
            resp = fetch(self.url, data=self.data, **request_kwargs)
            testcase.assertEqual(resp.status_code, 403, "No perm " + self.url)
            user = self.user
            perm = Permission.objects.get(codename=self.require_perm)
            user.user_permissions.add(perm)
            user.save()
            self.user.save()
        if self.user is None:
            client.logout()
        else:
            user = self.user
            client.force_login(
                user,
                backend='django.contrib.auth.backends.ModelBackend'
            )
        resp = fetch(self.url, data=self.data, **request_kwargs)
        if "debug" in request_kwargs:
            print(resp)
            print(resp.content)
            print(resp.resolver_match)
        testcase.assertEqual(resp.status_code, self.status, self.msg)
        if self.status == 200 and not self._ajax:
            if hasattr(resp, "context") and resp.context is not None:
                if "follow" not in request_kwargs and not skip_title:
                    testcase.assertTrue(
                        "page_title" in resp.context,
                        "Page title " + self.url)
                    testcase.assertTrue(
                        resp.context["page_title"],
                        "Page title " + self.url)
            for test in self.tests:
                testcase.assertTrue(test(resp), getattr(test, "msg", ""))
        self.resp = resp
        return resp

    def __str__(self):
        return str((self.url, self.method, self.status))


class JsonURL(TestURL):

    def __init__(self, *args, **kwargs):
        self._old_status = kwargs.get("status", 200)
        kwargs["status"] = 200
        super().__init__(*args, **kwargs)
        self._ajax = True

    @TestURL.status.setter
    def status(self, val):
        self._old_status = val

    def test(self, forbidden=False, not_found=False, **kwargs):
        if forbidden:
            status = self.status
            self._status = self._old_status # instead of 403, for 40* status
            resp = super().test(**kwargs)
            self._status = status
            return resp
        if not_found:
            status = self.status
            self._status = 404
            resp = super().test(**kwargs)
            self._status = status
            return resp
        resp = super().test(**kwargs)
        testcase = self._testcase
        body = resp.json()
        json_code = body.get("status")
        if self._old_status == 200:
            testcase.assertEqual(json_code, json_utils.OK, self.msg + " " + str(body))
        else:
            testcase.assertEqual(json_code, json_utils.ERROR, self.msg + " " + str(body))
        return resp
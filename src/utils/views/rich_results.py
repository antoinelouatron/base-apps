import abc
import json

from django.apps import apps as django_apps
from django.conf import settings

class RichResults():

    def __init__(self):
        self.items = []
    
    def add(self, result):
        """
        Add a result, returns self
        """
        self.items.append(result.as_dict())
        return self
    
    def __str__(self):
        if len(self.items) == 0:
            return ""
        elif len(self.items) == 1:
            return json.dumps(self.items[0])
        else:
            return json.dumps(self.items)
    
    def __bool__(self):
        return bool(len(self.items))

class BaseRichItem(abc.ABC):

    # if True, it's the base element of a result and we include @context
    # if False, it's an itemList.
    standalone = True

    @property
    @abc.abstractmethod
    def type(self):
        return None

    @property
    def base_dict(self):
        if self.standalone:
            return {
                "@context": "https://schema.org",
                "@type": self.type
            }
        return {
            "@type": self.type
        }
    
    def __init__(self, data=None, **kwargs):
        """
        Add the data dict and kwargs to dict representation of self
        """
        self.data = data or {}
        self.data.update(**kwargs)
    
    def as_dict(self):
        bd = self.base_dict
        bd.update(self.data)
        return bd
    
    @classmethod
    def domain(cls):
        if not hasattr(cls, "_domain"):
            Site = django_apps.get_model("sites.Site")
            site = Site.objects.get_current()
            cls._domain = site.domain
        return cls._domain


class ItemList(BaseRichItem):

    @property
    def type(self):
        return "ItemList"

    def __init__(self, items=None, data=None, **kwargs):
        super().__init__(data=data, **kwargs)
        items = items or []
        items = [it.as_dict() for it in items]
        for i in range(len(items)):
            items[i]["position"] = i + 1
        self.data["itemListElement"] = items
    
    def add_item(self, item):
        it = item.as_dict()
        it["position"] = len(self.data["itemListElement"]) + 1
        self.data["itemListElement"].append(it)
    
    def __len__(self):
        return len(self.data["itemListElement"])

class BreadCrumbList(ItemList):

    @property
    def type(self):
        return "BreadcrumbList"
    

class ListItem(BaseRichItem):

    standalone = False

    @property
    def type(self):
        return "ListItem"

class BreadCrumListItem(ListItem):
    
    @staticmethod
    def from_MenuItem(menu_item):
        return BreadCrumListItem(
            name=menu_item.current or menu_item.title,
            item="{}://{}{}".format(
                settings.DEFAULT_PROTOCOL,
                BaseRichItem.domain(),
                menu_item.url
            )
        )

class CourseItem(BaseRichItem):

    provider = {
        "@type": "Person",
        "name": "Antoine Louatron",
        "jobTitle": "Enseignant de mathématiques"
    }

    @property
    def type(self):
        return "Course"
    
    def __init__(self, data=None, **kwargs):
        super().__init__(data=data, **kwargs)
        self.data["provider"] = self.provider
    
    @staticmethod
    def from_Chapter(chap, standalone=True):
        data = {
            "name": chap.title,
            "description": chap.description,
        }
        if not standalone:
            data["url"] = "{}://{}{}".format(
                settings.DEFAULT_PROTOCOL,
                BaseRichItem.domain(),
                chap.get_absolute_url()
            )
        item = CourseItem(data=data)
        item.standalone = standalone
        return item
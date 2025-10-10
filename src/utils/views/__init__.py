"""
date: 2024-03-02

Mirror common class bases views with AssetsMixin added
"""

from typing import Any
from django.views.generic import base, edit, detail, list
from utils.views import class_view
from utils.views.mixins import AssetsMixin, UserIsStaffMixin

def _patch_context(cls):
    class Inner(cls, AssetsMixin):
        def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
            ctx = super().get_context_data(**kwargs)
            ctx.update(self.base_context_data(**kwargs))
            return ctx
    return Inner


#TemplateView = _patch_context(base.TemplateView)
CreateView = _patch_context(edit.CreateView)
#UpdateView = _patch_context(edit.UpdateView)
DeleteView = _patch_context(edit.DeleteView)
FormView = _patch_context(edit.FormView)
#DetailView = _patch_context(detail.DetailView)
#ListView = _patch_context(list.ListView)
CreateUpdateView = _patch_context(class_view.CreateUpdateView)
View = _patch_context(base.View)

# Patched views. Workaround type hinting, by subclassing directly.
class ListView(list.ListView, AssetsMixin):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context_data(**kwargs))
        return ctx

class TemplateView(base.TemplateView, AssetsMixin):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context_data(**kwargs))
        return ctx
    
class DetailView(detail.DetailView, AssetsMixin):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context_data(**kwargs))
        return ctx

class UpdateView(edit.UpdateView, AssetsMixin):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.base_context_data(**kwargs))
        return ctx

    def get_object(self, queryset=None): # cache result
        obj = getattr(self, "object", super().get_object(queryset))
        return obj
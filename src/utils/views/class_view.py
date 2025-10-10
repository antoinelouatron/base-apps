from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView

class CreateUpdateView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    
    template_name_suffix = "_form" # emulate django behaviour

    def get_object(self, queryset=None):
        if not hasattr(self, "object"): # cache the result
            try:
                self.object = super().get_object(queryset)
            except AttributeError:
                # SingleObjectMixin raises AttributeError if no url kwarg is found
                self.object = None
        self._edit_mode = self.object is not None
        return self.object

    # dispatch don't mix well with access Mixins
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["edition_mode"] = self._edit_mode
        return ctx
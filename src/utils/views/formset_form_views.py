from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.forms import models as model_forms
from django.http import HttpResponseRedirect
from django.views.generic import edit, detail

from utils.views.mixins import AssetsMixin

class FormsetFormMixin(AssetsMixin, edit.FormMixin):
    """Handle an additional formset.
    Inherits from FormMixin.

    Additional attributes :
    - formset_initial = {}
    - formset_class = None
    - formset_prefix = "formset"

    Additional methods :
    - get_formset_initial
    - get_formset_kwargs
    - get_formset_class

    Changed signature : form_valid and form_invalid takes an extra formset required argument
    """

    formset_initial = {}
    formset_class = None
    formset_prefix = "formset"

    def get_formset_class(self):
        return self.formset_class

    def get_formset_initial(self):
        """Return the initial data to use for formsets."""
        return self.formset_initial.copy()
    
    def get_formset_prefix(self):
        return self.formset_prefix

    def get_formset_kwargs(self):
        """Return the keyword arguments for instantiating the formset."""
        kwargs = {
            "initial": self.get_formset_initial(),
            "prefix": self.get_formset_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_formset(self, formset_class=None):
        """Return an instance of the formset to be used in this view."""
        if formset_class is None:
            formset_class = self.get_formset_class()
        return formset_class(**self.get_formset_kwargs())
    
    def form_valid(self, form, formset):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, formset):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(
            form=form, formset=formset))

    def get_context_data(self, **kwargs):
        """Insert the form and the formset into the context dict."""
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()
        if "formset" not in kwargs:
            kwargs["formset"] = self.get_formset()
        ctx = super().get_context_data(**kwargs)
        base_ctx = self.base_context_data()
        base_ctx.update(ctx)
        return base_ctx


class ModelFormsetFormMixin(FormsetFormMixin, edit.ModelFormMixin):

    formset_fields = None
    formset_model = None
    formset_queryset = None

    def get_formset_queryset(self):
        return self.formset_queryset

    def get_formset_class(self):
        """Return the formset class to use in this view.
        Override to make use of inline formsets or provide a formset class.
        """
        if self.formset_fields is not None and self.formset_class:
            raise ImproperlyConfigured(
                "Specifying both 'formset_fields' and 'formset_class' is not permitted."
            )
        if self.formset_class:
            return self.formset_class
        else:
            if self.formset_model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_formset_queryset().model
            if self.formset_fields is None:
                raise ImproperlyConfigured(
                    "Using ModelFormsetFormMixin (base class of %s) without "
                    "the 'formset_fields' attribute is prohibited." % self.__class__.__name__
                )
            return model_forms.modelformset_factory(model, fields=self.formset_fields)
    
    def get_formset_kwargs(self):
        kwargs = super().get_formset_kwargs()
        qset = self.get_formset_queryset()
        if qset is not None: # use custom queryset to build represented instances
            kwargs.update({"queryset": self.get_formset_queryset()})
        if hasattr(self, "object") and self.object is not None: # to use inlineformset
            kwargs.update({"instance": self.object})
        return kwargs

    def adjust_formset(self, formset) -> bool:
        """
        Hook to take actions on the formset after standalone form
        has been sucessfully saved. The form instance value is accessible in
        self.object

        Returns a boolean indicating if we can procedd to the formset saving.
        In case of False return value, form saving is rolled back.
        """
        # in case of inlineformset, update instance object with new main
        # object
        formset.instance = self.object
        return True
    
    def formset_post_save(self, form, formset) -> None:
        """
        Second hook, after all has been saved and before redirection
        """
        return
    
    def form_valid(self, form, formset):
        """If the form is valid, save the associated model."""
        with transaction.atomic():
            self.object = form.save()
            success = self.adjust_formset(formset)
            if success:
                formset.save()
                self.formset_post_save(form, formset)
                return super().form_valid(form, formset)
        transaction.rollback()
        return self.form_invalid(form, formset)
    
class ProcessFormsetFormView(edit.ProcessFormView):

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)

class CreateView(detail.SingleObjectTemplateResponseMixin,
                 ModelFormsetFormMixin, ProcessFormsetFormView):
    
    template_name_suffix = "_form" # emulate django behaviour

    def get(self, request, *args, **kwargs):
        self.object = None
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super().post(request, *args, **kwargs)

class UpdateView(detail.SingleObjectTemplateResponseMixin,
        ModelFormsetFormMixin, ProcessFormsetFormView):
    
    template_name_suffix = "_form" # emulate django behaviour

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

# class CreateUpdateView(detail.SingleObjectTemplateResponseMixin,
#                  ModelFormsetFormMixin, ProcessFormsetFormView):
    
#     template_name_suffix = "_form" # emulate django behaviour

#     def get_object(self, queryset=None):
#         if not hasattr(self, "object"): # cache the result
#             try:
#                 self.object = super().get_object(queryset)
#             except AttributeError:
#                 # SingleObjectMixin raises AttributeError if not url kwarg is found
#                 self.object = None
#         self._edit_mode = self.object is not None
#         return self.object

#     def get(self, request, *args, **kwargs):
#         self.object = self.get_object()
#         return super().get(request, *args, **kwargs)

#     def post(self, request, *args, **kwargs):
#         self.object = self.get_object()
#         return super().post(request, *args, **kwargs)
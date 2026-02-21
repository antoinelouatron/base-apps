"""
date: 2024-02-26
"""
import json
from typing import Any
from django.db import transaction
from django.http import HttpRequest
from django.http.response import HttpResponse as HttpResponse
from django.urls import reverse_lazy, reverse
from django import views
import agenda.forms as af
import agenda.models as am
from users.decorators import user_is_staff
from utils.views import FormView, mixins

class WeekManage(FormView):
    form_class = af.GenerateWeeks
    template_name = "agenda/week_manage.html"
    PAGE_TITLE = "Semaines de l'année."
    success_url = reverse_lazy("agenda:weeks")
    SCRIPTS = ["year"]

    @user_is_staff
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
    
    def get_active_weeks(self):
        return am.Week.objects.active().order_by("begin")
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["weeks"] = self.get_active_weeks()
        return ctx
    
    def popns(self, **kwargs):
        ns = super().popns(**kwargs)
        ns["urls.updateWeeks"] = reverse("agenda:weeks_update")
        return ns
    
    def get_all_menus(self, ctx):
        if self.request.user.is_staff:
            account = self.account_menu_items()
            account.mark_current("agenda")
            return [account]
        return []


class WeekNumberApi(mixins.JSONResponseMixin, views.View):

    @user_is_staff
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            cps = am.CollePlanning.objects.filter(week__active=True).select_related("week")
            cp_dic = {cp: cp.week.nb for cp in cps}
            with transaction.atomic():
                cps = cps.select_for_update()
                for d in data:
                    w = am.Week.objects.get(pk=d["id"])
                    w.label = d["label"]
                    w.nb = d["nb"]
                    w.save()
                week_mapping = {w.nb: w for w in am.Week.objects.filter(active=True)}
                changed_cps = []
                for cp, nb in cp_dic.items():
                    if nb in week_mapping:
                        cp.week = week_mapping[nb]
                        changed_cps.append(cp)
                    else:
                        raise ValueError(f"Le numéro de semaine {nb} n'existe pas.")
                am.CollePlanning.objects.bulk_update(changed_cps, ["week"])
            return self.ok({})
        except Exception as e:
            # import traceback
            # traceback.print_exception(e)
            return self.error(e)


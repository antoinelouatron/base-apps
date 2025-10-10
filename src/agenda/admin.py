from django.contrib import admin
import agenda.models as am
# Register your models here.
admin.site.register(am.Week)

class PeriodicAdmin(admin.ModelAdmin):
    list_display = ("__str__", "day_label", "periodicity", "_attendance_string")
    list_filter = ("day", "periodicity")
    ordering = ("day", "beghour")

admin.site.register(am.PeriodicEvent, PeriodicAdmin)
admin.site.register(am.BaseEvent)

class ColleEventAdmin(admin.ModelAdmin):
    list_display = ("__str__", "level", "classroom")
    list_filter = ("teacher", "level")
    ordering = ("level", "day", "beghour")
    list_editable = ("classroom",)

admin.site.register(am.ColleEvent)

class CollePlaningAdmin(admin.ModelAdmin):

    list_display = ("group__nb", "week__nb", "event")
    list_filter = ("event", )

admin.site.register(am.CollePlanning, CollePlaningAdmin)

admin.site.register(am.InscriptionEvent)
admin.site.register(am.ToDo)
admin.site.register(am.Note)
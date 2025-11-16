from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
#from django.contrib.auth.forms import UserChangeForm
from .models import (User, StudentColleGroup, ColleGroup, Level, Subject,
    AddDataTemplate)

class MyUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ("title", "display_name", "teacher", "student", "is_active", "last_login")
    list_filter = UserAdmin.list_filter + ("teacher", "student")
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("title", "teacher", "student")}),
    )
    actions = ["mark_active", "mark_inactive", "remove_student"]

    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    
    def remove_student(self, request, queryset):
        queryset.update(student=False)
    

admin.site.register(User, MyUserAdmin)

class SCGInline(admin.TabularInline):
    model = StudentColleGroup

class ColleGroupAdmin(admin.ModelAdmin):
    list_display = ("__str__", "level")
    ordering = ("level", "nb")
    list_filter = ("level",)
    inlines = [SCGInline]

admin.site.register(ColleGroup, ColleGroupAdmin)

admin.site.register(StudentColleGroup)
admin.site.register(Level)

class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "level")
    list_filter = ("level",)

admin.site.register(Subject, SubjectAdmin)
admin.site.register(AddDataTemplate)
from django.contrib import admin

from lizard_graph.models import GraphItem
from lizard_graph.models import GraphLayout
from lizard_graph.models import PredefinedGraph


class GraphItemInline(admin.TabularInline):
    model = GraphItem


class PredefinedGraphAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name", )}
    inlines = [GraphItemInline]


admin.site.register(GraphItem)
admin.site.register(GraphLayout)
admin.site.register(PredefinedGraph, PredefinedGraphAdmin)

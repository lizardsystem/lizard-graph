from django.contrib import admin

from lizard_graph.models import GraphItem
from lizard_graph.models import PredefinedGraph


class GraphItemInline(admin.TabularInline):
    model = GraphItem
    fields = ('location', 'parameter', 'module', 'time_step', 'qualifierset',
              'index', 'graph_type',
              'value', 'color', 'color_outside', 'line_width',
              'line_style', 'label', )


class PredefinedGraphAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name", )}
    inlines = [GraphItemInline]


admin.site.register(GraphItem)
admin.site.register(PredefinedGraph, PredefinedGraphAdmin)


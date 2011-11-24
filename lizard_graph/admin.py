from django.contrib import admin

from lizard_graph.models import GraphItem
from lizard_graph.models import GraphLayout
from lizard_graph.models import PredefinedGraph

from lizard_graph.models import HorizontalBarGraph
from lizard_graph.models import HorizontalBarGraphGoal
from lizard_graph.models import HorizontalBarGraphItem


class GraphItemInline(admin.TabularInline):
    model = GraphItem


class PredefinedGraphAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name", )}
    inlines = [GraphItemInline]


class HorizontalBarGraphItemInline(admin.TabularInline):
    model = HorizontalBarGraphItem


class HorizontalBarGraphAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name", )}
    inlines = [HorizontalBarGraphItemInline]


admin.site.register(GraphItem)
admin.site.register(GraphLayout)
admin.site.register(PredefinedGraph, PredefinedGraphAdmin)

admin.site.register(HorizontalBarGraph, HorizontalBarGraphAdmin)
admin.site.register(HorizontalBarGraphItem)
admin.site.register(HorizontalBarGraphGoal)

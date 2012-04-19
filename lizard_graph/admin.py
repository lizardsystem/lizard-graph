from django.contrib import admin

from lizard_graph.models import GraphItem
from lizard_graph.models import PredefinedGraph


class GraphItemInline(admin.TabularInline):
    model = GraphItem
    fields = ('location', 'related_location', 'parameter', 'module', 'time_step', 'qualifierset',
              'index', 'graph_type',
              'value', 'color', 'color_outside', 'line_width',
              'line_style', 'label', )

    def formfield_for_dbfield(self, db_field, **kwargs):
        """Trick to make the inline faster:

        http://ionelmc.wordpress.com/2012/01/19/tweaks-for-making-django-admin-faster/
        """
        formfield = super(GraphItemInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ['location', 'parameter', 'module', 'time_step', 'qualifierset']:
            # dirty trick so queryset is evaluated and cached in .choices
            formfield.choices = formfield.choices
        return formfield


class PredefinedGraphAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name", )}
    inlines = [GraphItemInline]


admin.site.register(GraphItem)
admin.site.register(PredefinedGraph, PredefinedGraphAdmin)


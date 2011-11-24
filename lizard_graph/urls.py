# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.contrib import admin
from django.views.generic import TemplateView

from lizard_ui.urls import debugmode_urlpatterns

from lizard_graph.views import GraphView
from lizard_graph.views import HorizontalBarGraphView


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$',
        GraphView.as_view(),
        name="lizard_graph_graph_view"),
    url(r'^bar/$',
        HorizontalBarGraphView.as_view(),
        name="lizard_graph_horizontal_bar_graph_view"),
    url(r'^examples/$',
        TemplateView.as_view(template_name="lizard_graph/examples.html")),
    )
urlpatterns += debugmode_urlpatterns()

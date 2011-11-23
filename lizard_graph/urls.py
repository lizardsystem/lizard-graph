# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.contrib import admin

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
    )
urlpatterns += debugmode_urlpatterns()

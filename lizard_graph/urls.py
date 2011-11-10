# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.conf.urls.defaults import include
from django.conf.urls.defaults import patterns
from django.conf.urls.defaults import url
from django.contrib import admin

from lizard_ui.urls import debugmode_urlpatterns

from lizard_graph.views import LineGraphView


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$',
        LineGraphView.as_view(),
        name="lizard_graph_line_graph_view"),
    )
urlpatterns += debugmode_urlpatterns()

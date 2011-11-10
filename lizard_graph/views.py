# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.views.generic.base import View
from django.http import HttpResponse

from lizard_fewsnorm.models import Series
from lizard_fewsnorm.models import GeoLocationCache

from nens_graph.common import NensGraph


class LineGraph(NensGraph):
    """
    Standard line graph.

    Inspired by lizard-map adapter.graph, but it is more generic."""

    def __init__(self, **kwargs):
        super(LineGraph, self).__init__(**kwargs)
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True)


class LineGraphView(View):
    """
    Draw standard line graph based on provided input.

    Input:
    """
    def get(self, request, *args, **kwargs):
        graph = LineGraph()

        # Testing
        location_id = 'ALM_237/1_Pomp-2'
        parameter_id = 'du.meting.omgezet2'
        location_cache = GeoLocationCache.objects.all()[0]
        db_name = location_cache.fews_norm_source.database_name
        series = Series.objects.using(db_name).filter(
            location__id=location_id,
            parameter__id=parameter_id)

        # Draw all series
        # for single_series in series:
        #     dates = []
        #     values = []
        #     for event in single_series.event_set.all():
        #         dates.append(event.timestamp)
        #         values.append(event.value)
        #     graph.axes.plot(
        #         dates,
        #         values,
        #         ls="o-",
        #         lw=2,
        #         label="lijntje")

        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
import datetime

from django.views.generic.base import View
from django.http import HttpResponse

from lizard_fewsnorm.models import Series
from lizard_fewsnorm.models import GeoLocationCache

from nens_graph.common import NensGraph
from timeseries import timeseries


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
        colors = ['green', 'blue']
        graph = LineGraph()

        # Testing
        location_id = '111.1'
        parameter_id = 'ALMR110'
        location_cache = GeoLocationCache.objects.all()[0]
        db_name = location_cache.fews_norm_source.database_name
        series = Series.objects.using(db_name).filter(
            location__id=location_id,
            parameter__id=parameter_id)
        start = datetime.datetime.now() - datetime.timedelta(days=365)
        end = datetime.datetime.now()
        ts = timeseries.TimeSeries.as_dict(series, start, end)

        color_index = 0

        for (loc, par), single_ts in ts.items():
            # print loc, par, single_ts
            dates = []
            values = []
            flag_dates = []
            flag_values = []
            event_items = sorted(single_ts.events.items(),
                                 key=lambda item: item[0])
            for timestamp, (value, flag, comment) in event_items:
                if value is not None:
                    dates.append(timestamp)
                    values.append(value)

                    # Flags:
                    # 0: Original/Reliable
                    # 1: Corrected/Reliable
                    # 2: Completed/Reliable
                    # 3: Original/Doubtful
                    # 4: Corrected/Doubtful
                    # 5: Completed/Doubtful
                    # 6: Missing/Unreliable
                    # 7: Corrected/Unreliable
                    # 8: Completed/Unreliable
                    # 9: Missing value
                    if flag > 2:
                        flag_dates.append(timestamp)
                        flag_values.append(flag)

            graph.axes.plot(
                dates,
                values,
                "-",
                color=colors[color_index],
                lw=2,
                label="lijntje")
            graph.axes.plot(
                flag_dates,
                flag_values,
                "o-",
                color='red',
                label="flag")
            color_index = (color_index + 1) % len(colors)

        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

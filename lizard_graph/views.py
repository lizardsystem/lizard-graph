# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
import datetime
import iso8601
import logging

from django.views.generic.base import View
from django.http import HttpResponse

from lizard_fewsnorm.models import Series
from lizard_fewsnorm.models import GeoLocationCache
from lizard_fewsnorm.models import FewsNormSource

from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import NensGraph
from timeseries import timeseries

logger = logging.getLogger(__name__)


class LineGraph(NensGraph):
    """
    Standard line graph.

    Inspired by lizard-map adapter.graph, but it is more generic."""

    def __init__(self, **kwargs):
        super(LineGraph, self).__init__(**kwargs)
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True)

        major_locator = LessTicksAutoDateLocator()
        self.axes.xaxis.set_major_locator(major_locator)

        major_formatter = MultilineAutoDateFormatter(
            major_locator, self.axes)
        self.axes.xaxis.set_major_formatter(major_formatter)

    def legend(self, handles=None, labels=None):
        """
        Add a legend to a graph.
        """
        handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            ncol = min(nitems, 3)
            # What comes next is an educated guess on the amount of
            # characters that can be used without collisions in the legend.
            ntrunc = int((self.width / ncol - 24) / 10)

            labels = [l[0:ntrunc] for l in labels]
            self.legend_obj = self.axes.legend(
                handles,
                labels,
                bbox_to_anchor=(0., 0., 1., 0.),
                loc='lower right',
                ncol=ncol,
                borderaxespad=0.,
                fancybox=True,
                shadow=True,)


class GraphViewMixin(object):
    """
    """

    def _time_series_from_request(self, request):
        """
        - location_id
        - parameter_id
        - module_id
        - dt_start
        - dt_end
        """
        location_id = request.GET.get('location_id', None)  # '111.1'
        parameter_id = request.GET.get('parameter_id', None)  # 'ALMR110'
        module_id = request.GET.get('module_id', None)

        start = request.GET.get('dt_start', None)
        end = request.GET.get('dt_end', None)

        if start is None:
            dt_start = datetime.datetime.now() - datetime.timedelta(days=365)
        else:
            dt_start = iso8601.parse_date(start)

        if end is None:
            dt_end = datetime.datetime.now()
        else:
            dt_end = iso8601.parse_date(end)

        # if location_id is not None:
        #     location_cache = GeoLocationCache.objects.filter(
        #         ident=location_id)[0]
        #     db_name = location_cache.fews_norm_source.database_name

        series = Series.objects.using(self.fews_norm_source.database_name).all()
        if location_id is not None:
            series = series.filter(location__id=location_id)
        if parameter_id is not None:
            series = series.filter(parameter__id=parameter_id)
        if module_id is not None:
            series = series.filter(module__id=module_id)

        ts = timeseries.TimeSeries.as_dict(series, dt_start, dt_end)
        return ts

    def _fews_norm_source_from_slug(self, slug):
        return FewsNormSource.objects.get(slug=slug)


class LineGraphView(View, GraphViewMixin):
    """
    Draw standard line graph based on provided input.

    Example request. Lizard-graph is mounted under 'graph', the source
    slug is 'test':

    http://127.0.0.1:8000/graph/test/line/?location_id=111.1&parameter_id=ALMR110&dt_start=2010-11-11%2000:00:00&dt_end=2011-11-11%2000:00:00

    """
    def get(self, request, *args, **kwargs):
        """
        Input:

        - fews_norm_source_slug (kwargs)
        - location_id
        - parameter_id
        - module_id
        - dt_start
        - dt_end

        TODO:
        - implement all kinds of lines, max, min, etc.
        """
        self.fews_norm_source = self._fews_norm_source_from_slug(
            kwargs['fews_norm_source_slug'])

        colors = ['green', 'blue']
        graph = LineGraph()

        ts = self._time_series_from_request(request)

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

        graph.legend()
        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

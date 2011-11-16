# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""
"""
import datetime
import iso8601
import logging

from django.views.generic.base import View
from django.http import HttpResponse
from django.utils import simplejson as json

from lizard_fewsnorm.models import Series
from lizard_fewsnorm.models import GeoLocationCache
from lizard_fewsnorm.models import FewsNormSource

from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import NensGraph
from timeseries import timeseries

logger = logging.getLogger(__name__)


class DateGridGraph(NensGraph):
    """
    Standard graph with a grid and dates on the x-axis.

    Inspired by lizard-map adapter.graph, but it is more generic.
    """
    def __init__(self, **kwargs):
        super(DateGridGraph, self).__init__(**kwargs)
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
            ncol = min(nitems, 2)
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

    def line_from_single_ts(self, single_ts, color, graph_item):
        """
        Draw line(s) from a single timeseries.

        Color is a matplotlib color, i.e. 'blue', 'black'

        Graph_item can contain an attribute 'layout'.
        """
        title = '%s - %s (%s)' % (
            single_ts.location_id, single_ts.parameter_id, single_ts.units)

        dates, values, flag_dates, flag_values = single_ts.dates_values()

        if not values:
            return

        # Line
        self.axes.plot(
            dates, values, "-", color=color, lw=2, label=title)

        # Flags
        self.axes.plot(
            flag_dates, flag_values, "o-", color='red',
            label=title + ' flags')

    def bar_from_single_ts(self, bar_status, single_ts, color, graph_item):
        """
        Draw bars.

        TODO: implement

        Graph_item can contain an attribute 'layout'.
        """

        # Make seconds from fews timesteps.
        TIME_STEPS = {'SETS1440': 1440 * 60}

        dates, values, flag_dates, flag_values = single_ts.dates_values()

        if not values:
            return

        self.axes.bar(dates, values, edgecolor='grey', width=60, label='test')


class TimeSeriesViewMixin(object):
    """
    A mixin for a view that uses fewsnorm timeseries.
    """

    def _time_series_from_graph_item(
        self, dt_start, dt_end, fews_norm_source_slug,
        location_id=None, parameter_id=None, module_id=None, type=None):
        """
        - fews_norm_source_slug
        - location_id (optional)
        - parameter_id (optional)
        - module_id (optional)
        """

        # fews_norm_source_slug = request.GET.get('fews_norm_source_slug', None)
        # location_id = request.GET.get('location_id', None)  # '111.1'
        # parameter_id = request.GET.get('parameter_id', None)  # 'ALMR110'
        # module_id = request.GET.get('module_id', None)
        # fews_norm_source = FewsNormSource.objects.get(
        #     slug=fews_norm_source_slug)
        fews_norm_source = FewsNormSource.objects.get(
            slug=fews_norm_source_slug)

        series = Series.objects.using(fews_norm_source.database_name).all()
        if location_id is not None:
            series = series.filter(location__id=location_id)
        if parameter_id is not None:
            series = series.filter(parameter__id=parameter_id)
        if module_id is not None:
            series = series.filter(module__id=module_id)

        ts = timeseries.TimeSeries.as_dict(series, dt_start, dt_end)
        return ts

    def _dt_from_request(self):
        """
        Get dt_start and dt_end from request. Revert to default.
        """
        start = self.request.GET.get('dt_start', None)
        end = self.request.GET.get('dt_end', None)

        if start is None:
            # A random default
            dt_start = datetime.datetime.now() - datetime.timedelta(days=365)
        else:
            dt_start = iso8601.parse_date(start)

        if end is None:
            # A random default
            dt_end = datetime.datetime.now()
        else:
            dt_end = iso8601.parse_date(end)

        return dt_start, dt_end

    def _dimensions_from_request(self):
        """
        Return width, height from request.
        """
        width = int(self.request.GET.get('width', 380))
        height = int(self.request.GET.get('height', 200))
        return width, height


class GraphView(View, TimeSeriesViewMixin):
    """
    Draw standard line graph based on provided input.

    See the README for details.
    """
    def _graph_items_from_request(self):
        """
        Return list of graph items from request.
        """
        get = self.request.GET
        predefined_graph = get.get('graph', None)
        print predefined_graph

        graph_items_json = self.request.GET.getlist('item')
        graph_items = [json.loads(graph_item_json)
                       for graph_item_json in graph_items_json]
        return graph_items

    def get(self, request, *args, **kwargs):
        """
        Input:
        - dt_start
        - dt_end
        - width
        - height

        - item={fews_norm_source_slug:.., location_id:..,
          parameter_id:.., module_id:.., type:.., arguments:..}
        - type can be 'line', 'stacked-bar', 'vertical-line',
          'horizontal-line', 'stacked-line' (see README).
        - items are processed in order.
        """
        default_colors = ['green', 'blue', 'yellow', 'magenta', ]
        graph = DateGridGraph()

        dt_start, dt_end = self._dt_from_request()
        width, height = self._dimensions_from_request()
        graph_items = self._graph_items_from_request()
        print graph_items

        color_index = 0
        # bar_status is to keep track of the height of stacked bars.
        bar_status = {}
        for index, graph_item in enumerate(graph_items):
            ts = self._time_series_from_graph_item(
                dt_start, dt_end, **graph_item)
            item_type = graph_item['type']

            for (loc, par), single_ts in ts.items():
                color = default_colors[color_index]
                if item_type == 'line':
                    graph.line_from_single_ts(single_ts, color, graph_item)
                elif item_type == 'bar':
                    bar_status = graph.bar_from_single_ts(
                        bar_status, single_ts, color, graph_item)

                color_index = (color_index + 1) % len(default_colors)

        graph.legend()
        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

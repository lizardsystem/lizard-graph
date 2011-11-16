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
from lizard_fewsnorm.models import ParameterCache
from lizard_fewsnorm.models import ModuleCache

from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem
from lizard_graph.models import GraphLayout

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

        if dt_end >= dt_start:
            return dt_start, dt_end
        else:
            return dt_end, dt_start

    def _dimensions_from_request(self):
        """
        Return width, height from request.
        """
        try:
            width = int(self.request.GET['width'])
        except (ValueError, KeyError):
            width = 380
        try:
            height = int(self.request.GET['height'])
        except (ValueError, KeyError):
            height = 200
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
        result = []
        get = self.request.GET

        # Using the shortcut graph=<graph-slug>
        predefined_graph_slug = get.get('graph', None)
        if predefined_graph_slug is not None:
            # Add all graph items of graph to result
            predefined_graph = PredefinedGraph.objects.get(
                slug=predefined_graph_slug)
            result.extend(predefined_graph.graphitem_set.all())

        # All standard items: make memory objects of them.
        graph_items_json = self.request.GET.getlist('item')
        for graph_item_json in graph_items_json:
            # Create memory object for each graph_item and append to result.
            graph_item_dict = json.loads(graph_item_json)
            print graph_item_dict
            graph_item = GraphItem()
            if 'type' in graph_item_dict:
                graph_item.graph_type = GraphItem.GRAPH_TYPES_REVERSE[
                    graph_item_dict['type']]
            if 'location' in graph_item_dict:
                location = GeoLocationCache(ident=graph_item_dict['location'])
                graph_item.location = location
            if 'parameter' in graph_item_dict:
                parameter = ParameterCache(ident=graph_item_dict['parameter'])
                graph_item.parameter = parameter
            if 'module' in graph_item_dict:
                module = ModuleCache(ident=graph_item_dict['module'])
                graph_item.module = module
            if 'polarization' in graph_item_dict:
                graph_item.value = graph_item_dict['polarization']
            if 'period' in graph_item_dict:
                graph_item.period = GraphItem.PERIOD_REVERSE[
                    graph_item_dict['period']]
            if 'reset-period' in graph_item_dict:
                graph_item.period = GraphItem.PERIOD_REVERSE[
                    graph_item_dict['reset-period']]
            if 'aggregation' in graph_item_dict:
                graph_item.period = GraphItem.PERIOD_REVERSE[
                    graph_item_dict['aggregation']]
            if 'layout' in graph_item_dict:
                layout_dict = graph_item_dict['layout']
                layout = GraphLayout()
                if 'color' in layout_dict:
                    layout.color = layout_dict['color']
                if 'color-outside' in layout_dict:
                    layout.color_outside = layout_dict['color-outside']
                if 'line-width' in layout_dict:
                    layout.color_outside = layout_dict['line-width']
                if 'line-style' in layout_dict:
                    layout.color_outside = layout_dict['line-style']
                graph_item.layout = layout
            result.append(graph_item)

        return result

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

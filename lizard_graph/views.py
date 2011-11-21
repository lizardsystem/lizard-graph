# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""
"""
import datetime
import iso8601
import logging
from matplotlib.dates import date2num

from django.db.models import Avg
from django.db.models import Min
from django.db.models import Max
from django.db.models import Sum
from django.views.generic.base import View
from django.http import HttpResponse
from django.utils import simplejson as json

from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem

from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import NensGraph

from timeseries import timeseries


logger = logging.getLogger(__name__)


def dates_values(timeseries):
    """
    Return lists of dates, values, flag_dates and flag_values.

    Accepts single timeseries. Easy when using matplotlib.
    """
    dates = []
    values = []
    flag_dates = []
    flag_values = []
    for timestamp, (value, flag, comment) in timeseries.sorted_event_items():
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
    return dates, values, flag_dates, flag_values


def time_series_aggregated(qs, start, end,
                           aggregation, aggregation_period, polarization=None):
    """
    Aggregated time series. Based on TimeSeries._from_django_QuerySet.

    It was not handy to integrate this into
    TimeSeries, because the import function would explode.

    Postgres SQL that aggregates:

        select date_part('year', datetime) as year, date_part('month', datetime) as month, sum(scalarvalue) from nskv00_opdb.timeseriesvaluesandflags group by year, month order by year, month;

        Event.objects.using('fewsnorm').filter(timestamp__year=2011).extra({'month': "date_part('month', datetime)", 'year': "date_part('year', datetime)"}).values('year', 'month').annotate(Sum('value'), Max('flag'))

        Event.objects.using('fewsnorm').filter(timestamp__year=2011).extra({'month': "date_part('month', datetime)", 'year': "date_part('year', datetime)", 'day': "date_part('day', datetime)"}).values('year', 'month', 'day').annotate(Sum('value'), Max('flag')).order_by('year', 'month', 'day')
    """
    POLARIZATION = {'negative': -1}

    result = {}
    # Convert aggregation vars from strings to defined constants
    aggregation_period = PredefinedGraph.PERIOD_REVERSE[aggregation_period]
    aggregation = PredefinedGraph.AGGREGATION_REVERSE[aggregation]
    multiplier = POLARIZATION.get(polarization, 1)

    for series in qs:
        obj = timeseries.TimeSeries()
        event = None
        event_set = series.event_set.all()
        if start is not None:
            event_set = event_set.filter(timestamp__gte=start)
        if end is not None:
            event_set = event_set.filter(timestamp__lte=end)

        # Aggregation period
        if aggregation_period == PredefinedGraph.PERIOD_YEAR:
            event_set = event_set.extra(
                {'year': "date_part('year', datetime)"}).values(
                'year').order_by('year')
        elif (aggregation_period == PredefinedGraph.PERIOD_MONTH or
              aggregation_period == PredefinedGraph.PERIOD_QUARTER):
            event_set = event_set.extra(
                {'year': "date_part('year', datetime)",
                 'month': "date_part('month', datetime)", }).values(
                'year', 'month').order_by('year', 'month')
        elif aggregation_period == PredefinedGraph.PERIOD_DAY:
            event_set = event_set.extra(
                {'year': "date_part('year', datetime)",
                 'month': "date_part('month', datetime)",
                 'day': "date_part('day', datetime)", }).values(
                'year', 'month', 'day').order_by('year', 'month', 'day')
        # Aggregate value and flags
        if aggregation == PredefinedGraph.AGGREGATION_AVG:
            event_set = event_set.annotate(Max('flag'), agg=Avg('value'))
        elif aggregation == PredefinedGraph.AGGREGATION_SUM:
            event_set = event_set.annotate(Max('flag'), agg=Sum('value'))
        # Event is now a dict with keys agg, flag__max, year,
        # month (if applicable, default 1), day (if
        # applicable, default 1).
        for event in event_set:
            timestamp = datetime.datetime(
                int(event['year']),
                int(event.get('month', 1)),
                int(event.get('day', 1)))
            # Comments are lost
            obj[timestamp] = (event['agg'] * multiplier,
                              event['flag__max'], '')

        if event is not None:
            ## nice: we ran the loop at least once.
            obj.location_id = series.location.id
            obj.parameter_id = series.parameter.id
            obj.time_step = series.timestep.id
            obj.units = series.parameter.groupkey.unit
            ## and add the TimeSeries to the result
            result[(obj.location_id, obj.parameter_id)] = obj
    return result


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

    def line_from_single_ts(self, single_ts, graph_item, default_color=None):
        """
        Draw line(s) from a single timeseries.

        Color is a matplotlib color, i.e. 'blue', 'black'

        Graph_item can contain an attribute 'layout'.
        """
        title = '%s - %s (%s)' % (
            single_ts.location_id, single_ts.parameter_id, single_ts.units)

        dates, values, flag_dates, flag_values = dates_values(single_ts)
        if not values:
            return

        layout = graph_item.layout_dict()
        color = layout.get('color', default_color)
        # Line
        self.axes.plot(dates, values, "-", color=color, lw=2, label=title)
        # Flags
        self.axes.plot(flag_dates, flag_values, "o-", color='red',
                       label=title + ' flags')

    def horizontal_line(self, value, layout, default_color=None):
        """
        Draw horizontal line.
        """
        self.axes.axhline(
            float(value),
            color=layout.get('color', default_color),
            lw=int(layout.get('line-width', 2)),
            ls=layout.get('line-style', '-'),
            label=layout.get('label', 'horizontale lijn'))

    def bar_from_single_ts(self, single_ts, graph_item,
                           default_color=None, bottom_ts=None):
        """
        Draw bars.

        Graph_item can contain an attribute 'layout'.

        Bottom_ts and single_ts MUST have the same timestamps. This
        can be accomplished by: single_ts = single_ts + bottom_ts * 0
        bottom_ts = bottom_ts + single_ts * 0
        """

        dates, values, flag_dates, flag_values = dates_values(single_ts)

        bottom = None
        if bottom_ts:
            bottom = dates_values(bottom_ts)

        if not values:
            return

        layout = graph_item.layout_dict()
        color = layout.get('color', default_color)
        color_outside = layout.get('color-outside', 'grey')

        title = '%s - %s (%s)' % (
            single_ts.location_id, single_ts.parameter_id, single_ts.units)

        style = {'color':color,
                 'edgecolor':color_outside,
                 'label':title}
        if bottom:
            style['bottom'] = bottom[1]  # 'values' of bottom
        self.axes.bar(dates, values, **style)


class TimeSeriesViewMixin(object):
    """
    A mixin for a view that uses fewsnorm timeseries.
    """

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


class GraphView(View, TimeSeriesViewMixin):
    """
    Draw standard line graph based on provided input.

    See the README for details.
    """

    def _graph_items_from_request(self):
        """
        Return list of graph items from request.

        The graph items are created in memory or retrieved from memory.
        """
        result = []
        graph_settings = {
            'aggregation-period': PredefinedGraph.PERIOD_MONTH,
            'aggregation': PredefinedGraph.AGGREGATION_SUM,
            'reset-period': PredefinedGraph.PERIOD_MONTH,
            'width': 1200,
            'height': 500,
            }
        get = self.request.GET

        # Using the shortcut graph=<graph-slug>
        predefined_graph_slug = get.get('graph', None)
        if predefined_graph_slug is not None:
            # Add all graph items of graph to result
            try:
                predefined_graph = PredefinedGraph.objects.get(
                    slug=predefined_graph_slug)
                graph_settings.update(predefined_graph.graph_settings())
                result.extend(predefined_graph.unfolded_graph_items())
            except PredefinedGraph.DoesNotExist:
                logger.exception("Tried to fetch a non-existing predefined "
                                 "graph %s" % predefined_graph_slug)

        # All standard items: make memory objects of them.
        graph_items_json = self.request.GET.getlist('item')
        for graph_item_json in graph_items_json:
            # Create memory object for each graph_item and append to result.
            graph_item_dict = json.loads(graph_item_json)
            graph_items = GraphItem.from_dict(graph_item_dict)
            result.extend(graph_items)

        # Graph settings can be overruled
        graph_parameters = [
            'title', 'x-label', 'y-label', 'y-range-min', 'y-range-max',
            'aggregation', 'aggregation-period', 'reset-period', 'width',
            'height']
        for graph_parameter in graph_parameters:
            if graph_parameter in get:
                graph_settings[graph_parameter] = get[graph_parameter]

        return result, graph_settings

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

        dt_start, dt_end = self._dt_from_request()
        graph_items, graph_settings = self._graph_items_from_request()
        graph = DateGridGraph(
            width=int(graph_settings['width']),
            height=int(graph_settings['height']))
        graph.axes.set_ymargin(0.1)

        color_index = 0
        ts_stacked_bar_sum = None
        ts_stacked_line_sum = None
        for index, graph_item in enumerate(graph_items):
            graph_type = graph_item.graph_type

            try:
                if graph_type == GraphItem.GRAPH_TYPE_LINE:
                    ts = graph_item.time_series(dt_start, dt_end)
                    for (loc, par), single_ts in ts.items():
                        graph.line_from_single_ts(
                            single_ts, graph_item,
                            default_color=default_colors[color_index])
                        color_index = (color_index + 1) % len(default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_HORIZONTAL_LINE:
                    graph.horizontal_line(
                        graph_item.value,
                        graph_item.layout_dict(),
                        default_color=default_colors[color_index])
                    color_index = (color_index + 1) % len(default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_STACKED_BAR:
                    qs = graph_item.series()
                    ts = time_series_aggregated(
                        qs, dt_start, dt_end,
                        aggregation=graph_settings['aggregation'],
                        aggregation_period=graph_settings['aggregation-period'])
                    for (loc, par), single_ts in ts.items():
                        # Make sure all timestamps are present.
                        if ts_stacked_bar_sum is None:
                            ts_stacked_bar_sum = single_ts * 0
                        ts_stacked_bar_sum += single_ts * 0
                        bar_status = graph.bar_from_single_ts(
                            single_ts, graph_item,
                            default_color=default_colors[color_index],
                            bottom_ts=ts_stacked_bar_sum)
                        ts_stacked_bar_sum += single_ts
                        color_index = (color_index + 1) % len(default_colors)
            except:
                # You never know if there is a bug somewhere
                logger.exception("Unknown error while drawing graph item.")

        graph.legend()
        graph.axes.set_xlim(date2num((dt_start, dt_end)))
        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

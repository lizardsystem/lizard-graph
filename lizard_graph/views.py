# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""
"""
import datetime
import iso8601
import logging
import math
from matplotlib.dates import date2num
from matplotlib.lines import Line2D
from sets import Set

from django.db.models import Avg
from django.db.models import Max
from django.db.models import Sum
from django.views.generic.base import View
from django.http import HttpResponse
from django.utils import simplejson as json

from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem
from lizard_graph.models import HorizontalBarGraph
#from lizard_graph.models import HorizontalBarGraphItem

from nens_graph.common import LessTicksAutoDateLocator
from nens_graph.common import MultilineAutoDateFormatter
from nens_graph.common import NensGraph

from timeseries import timeseries

from lizard_map.dateperiods import next_month
from lizard_map.dateperiods import next_year
from lizard_map.dateperiods import next_quarter
from lizard_map.dateperiods import next_day

from lizard_fewsnorm.models import GeoLocationCache


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
                           aggregation, aggregation_period, polarity=None):
    """
    Aggregated time series. Based on TimeSeries._from_django_QuerySet.

    It was not handy to integrate this into
    TimeSeries, because the import function would explode.

    Postgres SQL that aggregates:

        select date_part('year', datetime) as year, date_part('month',
        datetime) as month, sum(scalarvalue) from
        nskv00_opdb.timeseriesvaluesandflags group by year, month
        order by year, month;

        Event.objects.using('fewsnorm').filter(timestamp__year=2011).extra({
        'month':
        "date_part('month', datetime)", 'year': "date_part('year',
        datetime)"}).values('year', 'month').annotate(Sum('value'),
        Max('flag'))

        Event.objects.using('fewsnorm').filter(timestamp__year=2011).extra({
        'month':
        "date_part('month', datetime)", 'year': "date_part('year',
        datetime)", 'day': "date_part('day',
        datetime)"}).values('year', 'month',
        'day').annotate(Sum('value'), Max('flag')).order_by('year',
        'month', 'day')
    """
    POLARITIES = {'negative': -1}

    result = {}
    # Convert aggregation vars from strings to defined constants
    aggregation_period = PredefinedGraph.PERIOD_REVERSE[aggregation_period]
    aggregation = PredefinedGraph.AGGREGATION_REVERSE[aggregation]
    multiplier = POLARITIES.get(polarity, 1)

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


def time_series_cumulative(ts, reset_period):
    def next_border(dt, reset_period):
        reset_period = PredefinedGraph.PERIOD_REVERSE[reset_period]
        if reset_period == PredefinedGraph.PERIOD_DAY:
            next_start, next_end = next_day(dt)
        elif reset_period == PredefinedGraph.PERIOD_MONTH:
            next_start, next_end = next_month(dt)
        elif reset_period == PredefinedGraph.PERIOD_QUARTER:
            next_start, next_end = next_quarter(dt)
        elif reset_period == PredefinedGraph.PERIOD_YEAR:
            next_start, next_end = next_year(dt)
        return next_start

    result = ts.clone(with_events=True)

    last_event = None
    last_timestamp = None
    reset_border = None
    for timestamp, event in result.get_events():
        new_event = list(event)
        if reset_border is None:
            # Initial
            reset_border = next_border(timestamp, reset_period)
        if (last_timestamp and
            last_timestamp < reset_border and timestamp >= reset_border):
            # We're crossing the reset-border.
            reset_border = next_border(timestamp, reset_period)
            last_event = None
            last_timestamp = None
        if last_event is not None:
            new_event[0] += last_event[0]
        event_tuple = tuple(new_event)
        result[timestamp] = event_tuple
        last_event = event_tuple
        last_timestamp = timestamp

    return result


class DateGridGraph(NensGraph):
    """
    Standard graph with a grid and dates on the x-axis.

    Inspired by lizard-map adapter.graph, but it is more generic.

    Note: margin_extra_xx is defined, it looks like you can just stack
    stuff. But don't do that - for each item the total-final-height of
    _every_ component is needed to calculate the exact location in
    pixels. So if you wanna stack something, you need to recalculate
    all coordinates of components.
    """
    BAR_WIDTHS = {
        PredefinedGraph.PERIOD_DAY: 1,
        PredefinedGraph.PERIOD_MONTH: 30,
        PredefinedGraph.PERIOD_QUARTER: 90,
        PredefinedGraph.PERIOD_YEAR: 365,
        }

    MARGIN_TOP = 10
    MARGIN_BOTTOM = 25
    MARGIN_LEFT = 96
    MARGIN_RIGHT = 54

    def __init__(self, **kwargs):
        super(DateGridGraph, self).__init__(**kwargs)

        # # Calculate surrounding space. We want it to be a constant
        # # number of pixels. Safety check first.
        # if (self.width > self.MARGIN_LEFT + self.MARGIN_RIGHT and
        #     self.height > self.MARGIN_TOP + self.MARGIN_BOTTOM):

        #     self.figure.subplots_adjust(
        #         bottom=float(self.MARGIN_BOTTOM)/self.height,
        #         top=float(self.height-self.MARGIN_TOP)/self.height,
        #         left=float(self.MARGIN_LEFT)/self.width,
        #         right=float(self.width-self.MARGIN_RIGHT)/self.width)

        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True)

        major_locator = LessTicksAutoDateLocator()
        self.axes.xaxis.set_major_locator(major_locator)

        self.margin_top_extra = 0
        self.margin_bottom_extra = 0
        self.margin_left_extra = 0
        self.margin_right_extra = 0

        major_formatter = MultilineAutoDateFormatter(
            major_locator, self.axes)
        self.axes.xaxis.set_major_formatter(major_formatter)

    def graph_width(self):
        """
        Return the current width in pixels.

        This width is considered '1' in the matplotlib coordinate system.
        """
        width = self.width - (
            self.MARGIN_LEFT + self.margin_left_extra +
            self.MARGIN_RIGHT + self.margin_right_extra)
        return max(width, 1)

    def graph_height(self):
        """
        Return the current height in pixels.

        This height is considered '1' in the matplotlib coordinate system.
        """
        height = self.height - (
            self.MARGIN_TOP + self.margin_top_extra +
            self.MARGIN_BOTTOM + self.margin_bottom_extra)
        return max(height, 1)

    def legend(self, handles=None, labels=None, legend_location=0):
        """
        Add a legend to a graph.

        'best' 	0
        'upper right' 	1
        'upper left' 	2
        'lower left' 	3
        'lower right' 	4
        'right' 	5
        'center left' 	6
        'center right' 	7
        'lower center' 	8
        'upper center' 	9
        'center' 	10
        """
        if not handles or not labels:
            handles, labels = self.axes.get_legend_handles_labels()

        if handles and labels:
            nitems = len(handles)
            if legend_location in [5, 6, 7]:
                ncol = 1
                legend_lines = nitems
            else:
                ncol = min(nitems, 2)
                # What comes next is an educated guess on the amount of
                # characters that can be used without collisions in the legend.
                ntrunc = int((self.width / ncol - 24) / 10)
                labels = [l[0:ntrunc] for l in labels]
                legend_lines = int(math.ceil(float(nitems) / ncol))

            if legend_location in [3, 4, 8]:
                # 11 is margin for legend, 10 is line height, 6 is extra
                # In pixels
                self.margin_bottom_extra += legend_lines * 10 + 11 + 6
                legend_y = -float(self.margin_bottom_extra -
                                  3 +  # 3 is for bottom space
                                  self.MARGIN_BOTTOM) / self.graph_height()
                # quite stupid, but the coordinate system changes when you
                # use set_position. So the graph is on the negative side.

                # x, y, width, height
                bbox_to_anchor = (0., legend_y, 1., 0.)
            elif legend_location in [7, ]:
                # In pixels
                self.margin_right_extra += 210
                legend_x = 1 + float(self.margin_right_extra
                                     ) / self.graph_width()
                bbox_to_anchor = (legend_x, 0., 0., 1.)
            else:
                # default
                bbox_to_anchor = (0., 0., 1., 1.)

            self.legend_obj = self.axes.legend(
                handles,
                labels,
                bbox_to_anchor=bbox_to_anchor,
                loc=legend_location,
                ncol=ncol,
                borderaxespad=0.,
                fancybox=True,
                shadow=True,)

    def line_from_single_ts(self, single_ts, graph_item,
                            default_color=None, flags=False):
        """
        Draw line(s) from a single timeseries.

        Color is a matplotlib color, i.e. 'blue', 'black'

        Graph_item can contain an attribute 'layout'.
        """
        dates, values, flag_dates, flag_values = dates_values(single_ts)
        if not values:
            return

        layout = graph_item.layout_dict()

        label = layout.get('label', '%s - %s (%s)' % (
                single_ts.location_id, single_ts.parameter_id,
                single_ts.units))
        style = {
            'label': label,
            'color': layout.get('color', default_color),
            'lw': layout.get('line-width', 2),
            'ls': layout.get('line-style', '-'),
            }

        # Line
        self.axes.plot(dates, values, **style)
        # Flags: style is not customizable.
        if flags:
            self.axes.plot(flag_dates, flag_values, "o-", color='red',
                           label=label + ' flags')

    def horizontal_line(self, value, layout, default_color=None):
        """
        Draw horizontal line.
        """
        style = {
            'ls': layout.get('line-style', '-'),
            'lw': int(layout.get('line-width', 2)),
            'color': layout.get('color', default_color),
            }
        if 'label' in layout:
            style['label'] = layout['label']
        self.axes.axhline(float(value), **style)

    def vertical_line(self, value, layout, default_color=None):
        """
        Draw vertical line.
        """
        style = {
            'ls': layout.get('line-style', '-'),
            'lw': int(layout.get('line-width', 2)),
            'color': layout.get('color', default_color),
            }
        if 'label' in layout:
            style['label'] = layout['label']
        try:
            dt = iso8601.parse_date(value)
        except iso8601.ParseError:
            dt = datetime.datetime.now()
        self.axes.axvline(dt, **style)

    def bar_from_single_ts(self, single_ts, graph_item, bar_width,
                           default_color=None, bottom_ts=None):
        """
        Draw bars.

        Graph_item can contain an attribute 'layout'.

        Bottom_ts and single_ts MUST have the same timestamps. This
        can be accomplished by: single_ts = single_ts + bottom_ts * 0
        bottom_ts = bottom_ts + single_ts * 0

        bar_width in days
        """

        dates, values, flag_dates, flag_values = dates_values(single_ts)

        bottom = None
        if bottom_ts:
            bottom = dates_values(bottom_ts)

        if not values:
            return

        layout = graph_item.layout_dict()

        label = layout.get('label', '%s - %s (%s)' % (
            single_ts.location_id, single_ts.parameter_id, single_ts.units))

        style = {'color': layout.get('color', default_color),
                 'edgecolor': layout.get('color-outside', 'grey'),
                 'label': label,
                 'width': bar_width}
        if bottom:
            style['bottom'] = bottom[1]  # 'values' of bottom
        self.axes.bar(dates, values, **style)

    def set_margins(self):
        """
        Set the graph margins.

        Using MARGIN settings and margin_legend_bottom (in
        pixels). Call after adding legend and other stuff, just before
        png_response.
        """
        # Calculate surrounding space. We want it to be a constant
        # number of pixels. Safety check first, else just "do something".
        if (self.width > self.MARGIN_LEFT + self.margin_left_extra +
            self.MARGIN_RIGHT + self.margin_right_extra and
            self.height > self.MARGIN_TOP + self.margin_top_extra +
            self.MARGIN_BOTTOM + self.margin_bottom_extra):

            # x, y, width, height.. all from 0..1
            axes_x = float(self.MARGIN_LEFT +
                           self.margin_left_extra) / self.width
            axes_y = float(self.MARGIN_BOTTOM +
                           self.margin_bottom_extra) / self.height
            axes_width = float(self.width -
                               (self.MARGIN_LEFT +
                                self.margin_left_extra +
                                self.MARGIN_RIGHT +
                                self.margin_right_extra)) / self.width
            axes_height = float(self.height -
                                (self.MARGIN_TOP +
                                 self.margin_top_extra +
                                 self.MARGIN_BOTTOM +
                                 self.margin_bottom_extra)) / self.height
            self.axes.set_position((axes_x, axes_y, axes_width, axes_height))


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
    Draw graph based on provided input.

    You can draw lines, bars, stacked bars/lines, etc. See the README
    for details.
    """

    def _graph_items_from_request(self):
        """
        Return list of graph items from request.

        The graph items are created in memory or retrieved from memory.
        """
        result = []
        graph_settings = {
            'aggregation-period': 'month',
            'aggregation': 'sum',
            'reset-period': 'month',
            'width': 1200,
            'height': 500,
            'legend-location': -1,
            'flags': False,
            'now-line': False,
            }
        get = self.request.GET

        # Using the shortcut graph=<graph-slug>
        predefined_graph_slug = get.get('graph', None)
        if predefined_graph_slug is not None:
            # Add all graph items of graph to result
            location_get = get.get('location', None)
            if location_get is not None:
                # If multiple instances, just take one.
                try:
                    location_get = GeoLocationCache.objects.filter(
                        ident=location_get)[0]
                except IndexError:
                    # Beware: read-only.
                    logger.exception(
                        ('Tried to fetch a non-existing GeoLocationCache '
                         'object %s') % location_get)
                    location_get = GeoLocationCache(ident=location_get)
            try:
                predefined_graph = PredefinedGraph.objects.get(
                    slug=predefined_graph_slug)
                graph_settings.update(predefined_graph.graph_settings())
                result.extend(predefined_graph.unfolded_graph_items(
                        location=location_get))
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
            'height', 'legend-location', 'flags', 'now-line']
        for graph_parameter in graph_parameters:
            if graph_parameter in get:
                graph_settings[graph_parameter] = get[graph_parameter]

        # legend-location can be a numeric value (3), or it can be
        # text ("lower left").
        try:
            graph_settings['legend-location'] = int(
                graph_settings['legend-location'])
        except ValueError:
            pass

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
        # Get all graph items from request.
        graph_items, graph_settings = self._graph_items_from_request()
        graph = DateGridGraph(
            width=int(graph_settings['width']),
            height=int(graph_settings['height']))
        if ('y-range-min' not in graph_settings and
            'y-range-max' not in graph_settings):
            graph.axes.set_ymargin(0.1)

        bar_width = DateGridGraph.BAR_WIDTHS[PredefinedGraph.PERIOD_REVERSE[
            graph_settings['aggregation-period']]]
        graph.figure.suptitle(
            graph_settings.get('title', ''),
            x=0.5, y=1,
            horizontalalignment='center', verticalalignment='top')
        # Disappears somewhere, but not so important now...
        # graph.axes.set_xlabel(graph_settings.get('x-label', ''))
        graph.axes.set_ylabel(graph_settings.get('y-label', ''))

        color_index = 0
        ts_stacked_sum = {
            'bar-positive': 0,
            'bar-negative': 0,
            'line-cum': 0,
            'line': 0}
        # Let's draw these graph items.
        for graph_item in graph_items:
            graph_type = graph_item.graph_type

            try:
                if graph_type == GraphItem.GRAPH_TYPE_LINE:
                    ts = graph_item.time_series(dt_start, dt_end)
                    for (loc, par), single_ts in ts.items():
                        graph.line_from_single_ts(
                            single_ts, graph_item,
                            default_color=default_colors[color_index],
                            flags=graph_settings['flags'])
                        color_index = (color_index + 1) % len(default_colors)
                elif (graph_type ==
                      GraphItem.GRAPH_TYPE_STACKED_LINE_CUMULATIVE or
                      graph_type == GraphItem.GRAPH_TYPE_STACKED_LINE):
                    ts = graph_item.time_series(dt_start, dt_end)
                    for (loc, par), single_ts in ts.items():
                        if (graph_type == GraphItem.GRAPH_TYPE_STACKED_LINE):
                            current_ts = single_ts
                            stacked_key = 'line'
                        else:
                            current_ts = time_series_cumulative(
                                single_ts, graph_settings['reset-period'])
                            stacked_key = 'line-cum'
                        # cum_ts is bottom_ts + cumulative single_ts
                        # Make last observation carried forward
                        current_ts.is_locf = True
                        ts_stacked_sum[stacked_key] = (
                            current_ts + ts_stacked_sum[stacked_key])
                        graph.line_from_single_ts(
                            ts_stacked_sum[stacked_key], graph_item,
                            default_color=default_colors[color_index],
                            flags=False)
                        color_index = (color_index + 1) % len(default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_HORIZONTAL_LINE:
                    graph.horizontal_line(
                        graph_item.value,
                        graph_item.layout_dict(),
                        default_color=default_colors[color_index])
                    color_index = (color_index + 1) % len(default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_VERTICAL_LINE:
                    graph.vertical_line(
                        graph_item.value,
                        graph_item.layout_dict(),
                        default_color=default_colors[color_index])
                    color_index = (color_index + 1) % len(default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_STACKED_BAR:
                    qs = graph_item.series()
                    ts = time_series_aggregated(
                        qs, dt_start, dt_end,
                        aggregation=graph_settings['aggregation'],
                        aggregation_period=graph_settings[
                            'aggregation-period'])
                    if graph_item.value == 'negative':
                        stacked_key = 'bar-negative'
                        polarity = -1
                    else:
                        stacked_key = 'bar-positive'
                        polarity = 1
                    for (loc, par), single_ts in ts.items():
                        # Make sure all timestamps are present.
                        ts_stacked_sum[stacked_key] += single_ts * 0
                        abs_single_ts = polarity * abs(single_ts)
                        bar_status = graph.bar_from_single_ts(
                            abs_single_ts, graph_item, bar_width,
                            default_color=default_colors[color_index],
                            bottom_ts=ts_stacked_sum[stacked_key])
                        bar_status  # TODO: do something with it
                        ts_stacked_sum[stacked_key] += abs_single_ts
                        color_index = (color_index + 1) % len(default_colors)
            except:
                # You never know if there is a bug somewhere
                logger.exception("Unknown error while drawing graph item.")

        if graph_settings['legend-location'] >= 0:
            graph.legend(legend_location=graph_settings['legend-location'])

        graph.axes.set_xlim(date2num((dt_start, dt_end)))

        # Set ylim
        y_min = graph_settings.get('y-range-min', graph.axes.get_ylim()[0])
        y_max = graph_settings.get('y-range-max', graph.axes.get_ylim()[1])
        graph.axes.set_ylim(y_min, y_max)

        # Now line?
        if graph_settings.get('now-line', False):
            today = datetime.datetime.now()
            graph.axes.axvline(today, color='orange', lw=2, ls='--')

        # Set the margins, including legend.
        graph.set_margins()

        return graph.png_response(
            response=HttpResponse(content_type='image/png'))


def value_to_html_color(value):
    """
    Simple classifier for colors. All values will return a color.
    """
    if value < 0.2:
        return '#ff0000'
    if value < 0.4:
        return '#ffaa00'
    if value < 0.6:
        return '#ffff00'
    if value < 0.8:
        return '#00ff00'
    return '#0000ff'


class HorizontalBarGraphView(View, TimeSeriesViewMixin):
    """
    Display horizontal bars
    """

    def _graph_items_from_request(self):
        """
        Return graph_items and graph_settings

        graph_items must be a list with for each item a function
        time_series.  This function accepts keyword arguments dt_start
        and dt_end and returns a list of timeseries.
        """
        graph_settings = {
            'width': 1200,
            'height': 500,
            }
        get = self.request.GET

        location = get.get('location', None)
        if location is not None:
            try:
                location = GeoLocationCache.objects.filter(ident=location)[0]
            except IndexError:
                logger.exception(
                    ("Tried to fetch a non existing "
                     "GeoLocationCache %s, created dummy one") %
                    location)
                location = GeoLocationCache(ident=location)

        graph_items = []
        # Using the shortcut graph=<graph-slug>
        hor_graph_slug = get.get('graph', None)
        if hor_graph_slug is not None:
            # Add all graph items of graph to result
            try:
                hor_graph = HorizontalBarGraph.objects.get(
                    slug=hor_graph_slug)
                graph_items.extend(hor_graph.horizontalbargraphitem_set.all())
            except HorizontalBarGraph.DoesNotExist:
                logger.exception("Tried to fetch a non-existing hor.bar."
                                 "graph %s" % hor_graph_slug)

        # Graph settings can be overruled
        graph_parameters = ['width', 'height']
        for graph_parameter in graph_parameters:
            if graph_parameter in get:
                graph_settings[graph_parameter] = get[graph_parameter]

        return graph_items, graph_settings

    def get(self, request, *args, **kwargs):

        dt_start, dt_end = self._dt_from_request()
        graph_items, graph_settings = self._graph_items_from_request()
        graph = DateGridGraph(
            width=int(graph_settings['width']),
            height=int(graph_settings['height']))

        # # Legend. Must do this before using graph location calculations
        # legend_handles = [
        #     Line2D([], [], color=value_to_html_color(0.8), lw=10),
        #     Line2D([], [], color=value_to_html_color(0.6), lw=10),
        #     Line2D([], [], color=value_to_html_color(0.4), lw=10),
        #     Line2D([], [], color=value_to_html_color(0.2), lw=10),
        #     Line2D([], [], color=value_to_html_color(0.0), lw=10),
        #     ]
        # legend_labels = [
        #     'Zeer goed', 'Goed', 'Matig', 'Ontoereikend', 'Slecht']
        # graph.legend(legend_handles, legend_labels, legend_location=6)

        yticklabels = []
        block_width = (date2num(dt_end) - date2num(dt_start)) / 50
        collected_goal_timestamps = Set()

        for index, graph_item in enumerate(graph_items):
            yticklabels.append(graph_item.label)
            if not graph_item.location:
                graph_item.location = location
            # We want to draw a shadow past the end of the last
            # event. That's why we ignore dt_start.
            ts = graph_item.time_series(dt_end=dt_end)
            if len(ts) != 1:
                logger.warn('Warning: drawing %d timeseries on a single bar '
                            'HorizontalBarView', len(ts))
            # We assume there is only one timeseries.
            for (loc, par), single_ts in ts.items():
                dates, values, flag_dates, flag_values = dates_values(
                    single_ts)
                if not dates:
                    logger.warning('Tried to draw empty timeseries %s %s',
                                   loc, par)
                    continue
                block_dates = []
                block_dates_shadow = []
                for date_index in range(len(dates) - 1):
                    dist_to_next = (date2num(dates[date_index + 1]) -
                                    date2num(dates[date_index]))
                    this_block_width = min(block_width, dist_to_next)

                    block_dates.append(
                        (date2num(dates[date_index]), this_block_width))
                    block_dates_shadow.append(
                        (date2num(dates[date_index]), dist_to_next))

                block_dates.append(
                    (date2num(dates[-1]), block_width))
                # Ignoring tzinfo, otherwise we can't compare.
                last_date = max(dt_start.replace(tzinfo=None), dates[-1])
                block_dates_shadow.append(
                    (date2num(last_date),
                     (date2num(dt_end) - date2num(dt_start))))

                block_colors = [value_to_html_color(value)
                                for value in values]

                # Block shadow
                graph.axes.broken_barh(
                    block_dates_shadow, (index - 0.2, 0.4),
                    facecolors=block_colors, edgecolors=block_colors,
                    alpha=0.2)
                # The 'real' block
                graph.axes.broken_barh(
                    block_dates, (index - 0.4, 0.8),
                    facecolors=block_colors, edgecolors='grey')

            for goal in graph_item.goals.all():
                collected_goal_timestamps.update([goal.timestamp, ])

        # For each unique bar goal timestamp, generate a mini
        # graph. The graphs are ordered by timestamp.
        goal_timestamps = list(collected_goal_timestamps)
        goal_timestamps.sort()
        subplot_numbers = [312, 313]
        for index, goal_timestamp in enumerate(goal_timestamps[:2]):
            axes_goal = graph.figure.add_subplot(subplot_numbers[index])
            axes_goal.set_yticks(range(len(yticklabels)))
            axes_goal.set_yticklabels('')
            axes_goal.set_xticks([0, ])
            axes_goal.set_xticklabels([goal_timestamp.year, ])
            for graph_item_index, graph_item in enumerate(graph_items):
                # 0 or 1 items
                goals = graph_item.goals.filter(timestamp=goal_timestamp)
                for goal in goals:
                    axes_goal.broken_barh(
                        [(-0.5, 1)], (graph_item_index - 0.4, 0.8),
                        facecolors=value_to_html_color(goal.value),
                        edgecolors='grey')
            axes_goal.set_xlim((-0.5, 0.5))
            axes_goal.set_ylim(-0.5, len(yticklabels) - 0.5)

            # Coordinates are related to the graph size - not graph 311
            bar_width_px = 12
            axes_x = float(graph.width -
                           (graph.MARGIN_RIGHT + graph.margin_right_extra) +
                           bar_width_px +
                           2 * bar_width_px * index
                           ) / graph.width
            axes_y = float(graph.MARGIN_BOTTOM +
                      graph.margin_bottom_extra) / graph.height
            axes_width = float(bar_width_px) / graph.width
            axes_height = float(graph.graph_height()) / graph.height
            axes_goal.set_position((axes_x, axes_y,
                                    axes_width, axes_height))

        graph.axes.set_yticks(range(len(yticklabels)))
        graph.axes.set_yticklabels(yticklabels)
        graph.axes.set_xlim(date2num((dt_start, dt_end)))
        graph.axes.set_ylim(-0.5, len(yticklabels) - 0.5)

        # Set the margins, including legend.
        graph.set_margins()

        return graph.png_response(
            response=HttpResponse(content_type='image/png'))

# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
"""
"""
import datetime
import iso8601
import logging
from matplotlib.dates import date2num

from django.core.cache import cache
from django.db.models import Avg
from django.db.models import Max
from django.db.models import Sum
from django.views.generic.base import View
from django.http import HttpResponse
from django.utils import simplejson as json

from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem

from nens_graph.common import DateGridGraph

from timeseries import timeseries

from lizard_map.dateperiods import next_month
from lizard_map.dateperiods import next_year
from lizard_map.dateperiods import next_quarter
from lizard_map.dateperiods import next_day

from lizard_fewsnorm.models import GeoLocationCache


logger = logging.getLogger(__name__)


# Used by time_series_aggregated to 'flag' a time series.
TIME_SERIES_ALL = 1
TIME_SERIES_POSITIVE = 2
TIME_SERIES_NEGATIVE = 3


def time_series_aggregated(qs, start, end,
                           aggregation, aggregation_period):
    """
    Aggregated time series. Based on TimeSeries._from_django_QuerySet.

    Result is a dictionary with timeseries. The keys are: (location,
    parameter, option), where option is TIME_SERIES_ALL,
    TIME_SERIES_POSITIVE or TIME_SERIES_NEGATIVE

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
    result = {}
    # Convert aggregation vars from strings to defined constants
    aggregation_period = PredefinedGraph.PERIOD_REVERSE[aggregation_period]
    aggregation = PredefinedGraph.AGGREGATION_REVERSE[aggregation]

    for series in qs:
        obj = {
            TIME_SERIES_ALL: timeseries.TimeSeries(),
            TIME_SERIES_POSITIVE: timeseries.TimeSeries(),
            TIME_SERIES_NEGATIVE: timeseries.TimeSeries()}

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
            value = event['agg']
            obj[TIME_SERIES_ALL][timestamp] = (
                value, event['flag__max'], '')
            if value >= 0:
                obj[TIME_SERIES_POSITIVE][timestamp] = (
                    value, event['flag__max'], '')
            else:
                obj[TIME_SERIES_NEGATIVE][timestamp] = (
                    value, event['flag__max'], '')

        if event is not None:
            for k in obj.keys():
                ## nice: we ran the loop at least once.
                obj[k].location_id = series.location.id
                obj[k].parameter_id = series.parameter.id
                obj[k].time_step = series.timestep.id
                #obj[k].moduleinstance = series.moduleinstance.id
                obj[k].units = series.parameter.groupkey.unit
                ## and add the TimeSeries to the result
                result[(obj[k].location_id, obj[k].parameter_id, k)] = obj[k]
    return result


def cached_time_series_aggregated(graph_item, start, end,
                                  aggregation, aggregation_period):
    """
    Cached version of the time_series_aggregated
    """
    def agg_time_series_key(
        graph_item, start, end, aggregation, aggregation_period):

        return ('ts_agg::%s:%s:%s:%s:%s:%s::%s:%s:%s:%s' % (
            graph_item.fews_norm_db_name, graph_item.location,
            graph_item.parameter, graph_item.module, graph_item.time_step,
            graph_item.qualifierset, start, end, aggregation,
            aggregation_period)).replace(' ', '_')
    cache_key = agg_time_series_key(graph_item, start, end, aggregation, aggregation_period)
    ts_agg = cache.get(cache_key)
    if ts_agg is None:
        qs = graph_item.series()
        ts_agg = time_series_aggregated(qs, start, end,
                                        aggregation, aggregation_period)
        cache.set(cache_key, ts_agg)
    return ts_agg


def cached_time_series_from_graph_item(graph_item, start, end):
    """
    Cached version of graph_item.time_series(start, end)
    """
    def time_series_key(graph_item, start, end):
        return ('ts::%s:%s:%s:%s:%s:%s::%s:%s' % (
            graph_item.fews_norm_db_name, graph_item.location,
            graph_item.parameter, graph_item.module, graph_item.time_step,
            graph_item.qualifierset, start, end)).replace(' ', '_')
    cache_key = time_series_key(graph_item, start, end)
    ts = cache.get(cache_key)
    if ts is None:
        ts = graph_item.time_series(start, end)
        cache.set(cache_key, ts)
    return ts


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
    BAR_WIDTHS = {
        PredefinedGraph.PERIOD_DAY: 1,
        PredefinedGraph.PERIOD_MONTH: 30,
        PredefinedGraph.PERIOD_QUARTER: 90,
        PredefinedGraph.PERIOD_YEAR: 365,
        }

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
            'format': 'png',
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
                    # Beware: read-only. Throw away this 'useless'
                    # exception message.
                    logger.error(
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
            'height', 'legend-location', 'flags', 'now-line', 'format', ]
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

        bar_width = GraphView.BAR_WIDTHS[PredefinedGraph.PERIOD_REVERSE[
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
                    ts = cached_time_series_from_graph_item(
                        graph_item, dt_start, dt_end)
                    for (loc, par), single_ts in ts.items():
                        graph.line_from_single_ts(
                            single_ts, graph_item,
                            default_color=default_colors[color_index],
                            flags=graph_settings['flags'])
                        color_index = (color_index + 1) % len(default_colors)
                elif (graph_type ==
                      GraphItem.GRAPH_TYPE_STACKED_LINE_CUMULATIVE or
                      graph_type == GraphItem.GRAPH_TYPE_STACKED_LINE):
                    ts = cached_time_series_from_graph_item(
                        graph_item, dt_start, dt_end)
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
                    ts = cached_time_series_aggregated(
                        graph_item, dt_start, dt_end,
                        aggregation=graph_settings['aggregation'],
                        aggregation_period=graph_settings[
                            'aggregation-period'])
                    if graph_item.value == 'negative':
                        stacked_key = 'bar-negative'
                        polarity = -1
                    else:
                        stacked_key = 'bar-positive'
                        polarity = 1
                    for (loc, par, option), single_ts in ts.items():
                        if option == TIME_SERIES_ALL:
                            # Make sure all timestamps are present.
                            ts_stacked_sum[stacked_key] += single_ts * 0
                            abs_single_ts = polarity * abs(single_ts)
                            graph.bar_from_single_ts(
                                abs_single_ts, graph_item, bar_width,
                                default_color=default_colors[color_index],
                                bottom_ts=ts_stacked_sum[stacked_key])
                            ts_stacked_sum[stacked_key] += abs_single_ts
                            color_index = (color_index + 1) % len(
                                default_colors)
                elif graph_type == GraphItem.GRAPH_TYPE_STACKED_BAR_SIGN:
                    ts = cached_time_series_aggregated(
                        graph_item, dt_start, dt_end,
                        aggregation=graph_settings['aggregation'],
                        aggregation_period=graph_settings[
                            'aggregation-period'])
                    if graph_item.value == 'negative':
                        stacked_key_positive = 'bar-negative'
                        stacked_key_negative = 'bar-positive'
                        polarity = {
                            TIME_SERIES_POSITIVE: -1,
                            TIME_SERIES_NEGATIVE: 1}
                    else:
                        stacked_key_positive = 'bar-positive'
                        stacked_key_negative = 'bar-negative'
                        polarity = {
                            TIME_SERIES_POSITIVE: 1,
                            TIME_SERIES_NEGATIVE: -1}
                    for (loc, par, option), single_ts in ts.items():
                        # Make sure all timestamps are present.
                        if option == TIME_SERIES_POSITIVE:
                            stacked_key = stacked_key_positive
                        elif option == TIME_SERIES_NEGATIVE:
                            stacked_key = stacked_key_negative
                        if (option == TIME_SERIES_POSITIVE or
                            option == TIME_SERIES_NEGATIVE):
                            ts_stacked_sum[stacked_key] += single_ts * 0
                            abs_single_ts = polarity[option] * abs(single_ts)
                            graph.bar_from_single_ts(
                                abs_single_ts, graph_item, bar_width,
                                default_color=default_colors[color_index],
                                bottom_ts=ts_stacked_sum[stacked_key])
                            ts_stacked_sum[stacked_key] += abs_single_ts
                            color_index = (color_index + 1) % len(
                                default_colors)
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

        response_format = graph_settings['format']
        if response_format == 'csv':
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = (
                'attachment; filename="%s.csv"' %
                graph_settings.get('title', 'grafiek'))
            graph.timeseries_csv(response)
            return response
        else:
            return graph.png_response(
                response=HttpResponse(content_type='image/png'))

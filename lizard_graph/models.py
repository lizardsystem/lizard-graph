# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.db import models

from lizard_fewsnorm.models import GeoLocationCache
from lizard_fewsnorm.models import ParameterCache
from lizard_fewsnorm.models import ModuleCache

from lizard_map.models import ColorField

from lizard_fewsnorm.models import Series
from timeseries import timeseries


class PredefinedGraph(models.Model):
    """
    Predefined graph. Graph entries must point to a predefined graph.
    """
    name = models.CharField(max_length=40)
    slug = models.SlugField(unique=True)
    description = models.TextField(null=True, blank=True)

    title = models.CharField(
        null=True, blank=True, max_length=80,
        help_text="Last filled in is used in graph")
    x_label = models.CharField(
        null=True, blank=True, max_length=80,
        help_text="Last filled in is used in graph")
    y_label = models.CharField(
        null=True, blank=True, max_length=80,
        help_text="Last filled in is used in graph")

    def __unicode__(self):
        return self.name

    def unfolded_graph_items(self, location=None):
        """
        Graph items can point to other predefined graphs, this unfolds it.
        """
        result = []
        for graph_item in self.graphitem_set.all():
            new_graph_items = graph_item.from_dict(graph_item.as_dict())
            # Add location if it is not already defined.
            if location is not None:
                for new_graph_item in new_graph_items:
                    if not new_graph_item.location:
                        new_graph_item.location = location
            result.extend(new_graph_items)
        return result


class GraphLayout(models.Model):
    """
    Layout that can be applied to a graph entry.

    Options that are used depend on the graph type defined in the
    graph entry.
    """
    color = ColorField(default='')
    color_outside = ColorField(default='',
        help_text="For stacked-bar, stacked-line and stacked-line-cum")
    line_width = models.FloatField(
        null=True, blank=True, default=None,
        help_text="For everything with lines")
    line_style = models.CharField(
        null=True, blank=True, max_length=10, default=None,
        help_text="For everything with lines")

    def __unicode__(self):
        return 'GraphLayout'

    @classmethod
    def from_dict(cls, layout_dict):
        layout = GraphLayout()
        if 'color' in layout_dict:
            layout.color = layout_dict['color']
        if 'color-outside' in layout_dict:
            layout.color_outside = layout_dict['color-outside']
        if 'line-width' in layout_dict:
            layout.line_width = layout_dict['line-width']
        if 'line-style' in layout_dict:
            layout.line_style = layout_dict['line-style']
        return layout

    def as_dict(self):
        result = {}
        if self.color:
            result['color'] = self.color
        if self.color_outside:
            result['color-outside'] = self.color_outside
        if self.line_width:
            result['line-width'] = self.line_width
        if self.line_style:
            result['line-style'] = self.line_style
        return result


class GraphItem(models.Model):
    """
    A single item for a graph - a line, bar or whatever.
    """
    GRAPH_TYPE_LINE = 1
    GRAPH_TYPE_VERTICAL_LINE = 2
    GRAPH_TYPE_HORIZONTAL_LINE = 3
    GRAPH_TYPE_STACKED_BAR = 4
    GRAPH_TYPE_STACKED_LINE = 5
    GRAPH_TYPE_STACKED_LINE_CUMULATIVE = 6
    GRAPH_TYPE_PREDEFINED_GRAPH = 7

    GRAPH_TYPE_CHOICES = (
        (GRAPH_TYPE_LINE, 'line'),
        (GRAPH_TYPE_VERTICAL_LINE, 'vertical-line'),
        (GRAPH_TYPE_HORIZONTAL_LINE, 'horizontal-line'),
        (GRAPH_TYPE_STACKED_BAR, 'stacked-bar'),
        (GRAPH_TYPE_STACKED_LINE, 'stacked-line'),
        (GRAPH_TYPE_STACKED_LINE_CUMULATIVE, 'stacked-line-cumulative'),
        (GRAPH_TYPE_PREDEFINED_GRAPH, 'predefined-graph'),
        )

    GRAPH_TYPES = dict(GRAPH_TYPE_CHOICES)
    GRAPH_TYPES_REVERSE = dict([(b, a) for a, b in GRAPH_TYPE_CHOICES])

    PERIOD_DAY = 1
    PERIOD_MONTH = 2
    PERIOD_QUARTER = 3
    PERIOD_YEAR = 4
    PERIOD_CHOICES = (
        (PERIOD_DAY, 'day'),
        (PERIOD_MONTH, 'month'),
        (PERIOD_QUARTER, 'quarter'),
        (PERIOD_YEAR, 'year'),
        )
    PERIOD = dict(PERIOD_CHOICES)
    PERIOD_REVERSE = dict([(b, a) for a, b in PERIOD_CHOICES])

    AGGREGATION_AVG = 1
    AGGREGATION_SUM = 2
    AGGREGATION_CHOICES = (
        (AGGREGATION_AVG, 'avg'),
        (AGGREGATION_SUM, 'sum'),
        )
    AGGREGATION = dict(AGGREGATION_CHOICES)
    AGGREGATION_REVERSE = dict([(b, a) for a, b in AGGREGATION_CHOICES])

    predefined_graph = models.ForeignKey(PredefinedGraph)
    index = models.IntegerField(default=100)

    graph_type = models.IntegerField(
        choices=GRAPH_TYPE_CHOICES, default=GRAPH_TYPE_LINE)

    location = models.ForeignKey(
        GeoLocationCache, null=True, blank=True,
        help_text=('Optional even if fewsnorm is used, because location '
                   'can be provided last-minute. If filled in, it overrides '
                   'the provided location'))
    parameter = models.ForeignKey(
        ParameterCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')
    module = models.ForeignKey(
        ModuleCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')

    value = models.CharField(
        null=True, blank=True, max_length=40,
        help_text=('Numeric value for horizontal-line and vertical-line. '
                   '"negative" for stacked-bar negative polarization. '
                   'Slug of predefined graph in case of predefined-graph.'))
    period = models.IntegerField(
        choices=PERIOD_CHOICES, null=True, blank=True,
        help_text=('Reset-period for stacked-line-cumulative or '
                   'aggregation period for stacked-bar'))
    aggregation = models.IntegerField(
        null=True, blank=True, choices=AGGREGATION_CHOICES,
        help_text='Required for stacked-bar')

    layout = models.ForeignKey(
        GraphLayout, blank=True, null=True, default=None)

    class Meta:
        ordering = ('index', )

    def __unicode__(self):
        return '%s %d' % (self.predefined_graph, self.index)

    @property
    def fews_norm_db_name(self):
        if self.location and self.location.fews_norm_source:
            return self.location.fews_norm_source.database_name
        else:
            return None

    def _require_fewsnorm(self):
        return self.graph_type in [
            GraphItem.GRAPH_TYPE_LINE,
            GraphItem.GRAPH_TYPE_STACKED_BAR,
            GraphItem.GRAPH_TYPE_STACKED_LINE,
            GraphItem.GRAPH_TYPE_STACKED_LINE_CUMULATIVE,
            ]

    def time_series(
        self, dt_start, dt_end, db_name=None):
        """
        Return dictionary of timeseries.

        Keys are (location, parameter), value is timeseries object.
        """
        if not self._require_fewsnorm():
            return {}
        if db_name is None:
            db_name = self.fews_norm_db_name
        if not db_name:
            return {}

        series = Series.objects.using(db_name).all()
        if self.location is not None:
            series = series.filter(location__id=self.location.ident)
        if self.parameter is not None:
            series = series.filter(parameter__id=self.parameter.ident)
        if self.module is not None:
            series = series.filter(module__id=self.module.ident)

        ts = timeseries.TimeSeries.as_dict(series, dt_start, dt_end)
        return ts

    @classmethod
    def from_dict(cls, graph_item_dict):
        """
        Return a GraphItem created from the provided dictionary.

        Note that objects are not saved. Fields predefined_graph nor
        index are filled.

        The provided dictionary can have the following keys:
        - type: 'line', 'vertical-line', etc.
        - location: fews location id
        - parameter: fews parameter id
        - module: fews module id
        - polarization (will be mapped to value)
        - value: depends on type
        - period: 'day', 'month', 'quarter' or 'year'
        - reset-period (will be mapped to period)
        - aggregation: 'avg' or 'sum'
        - layout: dict with optional keys color, color-inside,
          line-width, line-style
        """
        graph_type = GraphItem.GRAPH_TYPES_REVERSE[
            graph_item_dict['type']]
        location = None
        if 'location' in graph_item_dict:
            location = GeoLocationCache(ident=graph_item_dict['location'])

        if graph_type == GraphItem.GRAPH_TYPE_PREDEFINED_GRAPH:
            # This is a special case. Return underlying GraphItems
            predefined_graph = PredefinedGraph.objects.get(
                slug=graph_item_dict['value'])
            return predefined_graph.unfolded_graph_items(location)

        graph_item = GraphItem()
        graph_item.graph_type = graph_type
        graph_item.location = location
        if 'parameter' in graph_item_dict:
            parameter = ParameterCache(ident=graph_item_dict['parameter'])
            graph_item.parameter = parameter
        if 'module' in graph_item_dict:
            module = ModuleCache(ident=graph_item_dict['module'])
            graph_item.module = module
        if 'polariaztion' in graph_item_dict:
            graph_item.value = graph_item_dict['polarization']
        if 'value' in graph_item_dict:
            graph_item.value = graph_item_dict['value']
        if 'period' in graph_item_dict:
            graph_item.period = GraphItem.PERIOD_REVERSE[
                graph_item_dict['period']]
        if 'reset-period' in graph_item_dict:
            graph_item.period = GraphItem.PERIOD_REVERSE[
                graph_item_dict['reset-period']]
        if 'aggregation' in graph_item_dict:
            graph_item.aggregation = GraphItem.AGGREGATION_REVERSE[
                graph_item_dict['aggregation']]
        if 'layout' in graph_item_dict:
            layout_dict = graph_item_dict['layout']
            graph_item.layout = GraphLayout.from_dict(layout_dict)

        return [graph_item, ]

    def as_dict(self):
        """
        Return dictionary form of GraphItem.

        Can be used to recreate GraphItems using from_dict.
        """
        result = {
            'type': GraphItem.GRAPH_TYPES[self.graph_type],
            }
        if self.location is not None:
            result['location'] = self.location.ident
        if self.parameter is not None:
            result['parameter'] = self.parameter.ident
        if self.module is not None:
            result['module'] = self.module.ident
        if self.value is not None:
            result['value'] = self.value
        if self.period is not None:
            result['period'] = GraphItem.PERIOD[self.period]
        if self.aggregation is not None:
            result['aggregation'] = GraphItem.AGGREGATION[self.aggregation]
        if self.layout is not None:
            result['layout'] = self.layout.as_dict()
        return result

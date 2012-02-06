# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.db import models

from lizard_fewsnorm.models import GeoLocationCache
from lizard_fewsnorm.models import ModuleCache
from lizard_fewsnorm.models import ParameterCache
from lizard_fewsnorm.models import QualifierSetCache
from lizard_fewsnorm.models import TimeSeriesCache
from lizard_fewsnorm.models import TimeStepCache

from lizard_map.models import ColorField

from lizard_fewsnorm.models import Series
from timeseries import timeseries

import logging

logger = logging.getLogger(__name__)


class PredefinedGraphManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class PredefinedGraph(models.Model):
    """
    Predefined graph. Graph entries must point to a predefined graph.
    """
    objects = PredefinedGraphManager()

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

    # Matplotlib locations for legend
    LEGEND_LOCATION_CHOICES = (
        (-1, 'no legend'),
        (0, 'best'),
        (1, 'upper right'),
        (2, 'upper left'),
        (3, 'lower left'),
        (4, 'lower right'),
        (5, 'right'),
        (6, 'center left'),
        (7, 'center right'),
        (8, 'lower center'),
        (9, 'upper center'),
        (10, 'center'),
        )

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
    y_range_min = models.FloatField(null=True, blank=True,
                                    help_text='Y range min')
    y_range_max = models.FloatField(null=True, blank=True,
                                    help_text='Y range max')
    legend_location = models.IntegerField(
        choices=LEGEND_LOCATION_CHOICES, null=True, blank=True)

    aggregation = models.IntegerField(
        null=True, blank=True, choices=AGGREGATION_CHOICES,
        help_text='Required for stacked-bar')
    aggregation_period = models.IntegerField(
        choices=PERIOD_CHOICES, null=True, blank=True,
        help_text=('For stacked-bar'))
    reset_period = models.IntegerField(
        choices=PERIOD_CHOICES, null=True, blank=True,
        help_text=('For stacked-line-cumulative'))

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

    def graph_settings(self):
        result = {}
        if self.title:
            result['title'] = self.title
        if self.x_label:
            result['x-label'] = self.x_label
        if self.y_label:
            result['y-label'] = self.y_label
        if self.y_range_min is not None:
            result['y-range-min'] = self.y_range_min
        if self.y_range_max is not None:
            result['y-range-max'] = self.y_range_max
        if self.legend_location is not None:
            result['legend-location'] = self.legend_location

        if self.aggregation:
            result['aggregation'] = PredefinedGraph.AGGREGATION[self.aggregation]
        if self.aggregation_period:
            result['aggregation-period'] = PredefinedGraph.PERIOD[
                self.aggregation_period]
        if self.reset_period:
            result['reset-period'] = PredefinedGraph.PERIOD[self.reset_period]
        return result

    def natural_key(self):
        return (self.slug, )


class GraphLayoutMixin(models.Model):
    """
    Layout that can be applied to a graph entry.

    Options that are used depend on the graph type defined in the
    graph entry.
    """
    color = ColorField(null=True, blank=True, default='')
    color_outside = ColorField(null=True, blank=True, default='',
        help_text="For stacked-bar, stacked-line and stacked-line-cum")
    line_width = models.FloatField(
        null=True, blank=True,
        help_text="For everything with lines")
    line_style = models.CharField(
        null=True, blank=True, max_length=10, default=None,
        help_text="For everything with lines")
    label = models.CharField(max_length=80, blank=True, null=True)

    class Meta:
        abstract = True

    def apply_layout_dict(self, layout_dict):
        if 'color' in layout_dict:
            self.color = layout_dict['color']
        if 'color-outside' in layout_dict:
            self.color_outside = layout_dict['color-outside']
        if 'line-width' in layout_dict:
            self.line_width = layout_dict['line-width']
        if 'line-style' in layout_dict:
            self.line_style = layout_dict['line-style']
        if 'label' in layout_dict:
            self.label = layout_dict['label']

    def layout_as_dict(self):
        result = {}
        if self.color:
            result['color'] = self.color
        if self.color_outside:
            result['color-outside'] = self.color_outside
        if self.line_width:
            result['line-width'] = self.line_width
        if self.line_style:
            result['line-style'] = self.line_style
        if self.label:
            result['label'] = self.label
        return result


class GraphItemMixin(models.Model):
    """
    About location, parameter and modules and fetching timeseries.
    """
    # TODO: location_wildcard. See readme.
    # location_wildcard = models.CharField(
    #     max_length=200, null=True, blank=True,
    #     help_text=('If left empty, take location. If filled in and combined '
    #                'with the url parameter \'locations\', this field '
    #                'overrides the location field.'))
    location = models.ForeignKey(
        GeoLocationCache, null=True, blank=True,
        help_text=('Optional even if the data source fewsnorm is used, '
                   'because location '
                   'can be provided last-minute. If filled in, it overrides '
                   'the provided location'))
    parameter = models.ForeignKey(
        ParameterCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')
    module = models.ForeignKey(
        ModuleCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')
    time_step = models.ForeignKey(
        TimeStepCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')
    # Not qualifier_set because that conflicts with Django stuff.
    qualifierset = models.ForeignKey(
        QualifierSetCache, null=True, blank=True,
        help_text='For all types that require a fewsnorm source')

    class Meta:
        abstract = True

    @property
    def fews_norm_db_name(self):
        if self.location and self.location.fews_norm_source:
            return self.location.fews_norm_source.database_name
        else:
            return None

    def series(self, db_name=None):
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
            series = series.filter(moduleinstance__id=self.module.ident)
        return series

    def time_series(
        self, dt_start=None, dt_end=None, db_name=None):
        """
        Return dictionary of timeseries.

        Keys are (location, parameter), value is timeseries object.
        """
        # if not self._require_fewsnorm():
        #     return {}

        series = self.series(db_name=db_name)
        ts = timeseries.TimeSeries.as_dict(
            series, dt_start, dt_end)
        return ts


class GraphItem(GraphItemMixin, GraphLayoutMixin):
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

    predefined_graph = models.ForeignKey(PredefinedGraph)
    index = models.IntegerField(default=100)

    graph_type = models.IntegerField(
        choices=GRAPH_TYPE_CHOICES, default=GRAPH_TYPE_LINE)

    value = models.CharField(
        null=True, blank=True, max_length=40,
        help_text=('Numeric value for horizontal-line and vertical-line. '
                   '"negative" for stacked-bar negative polarity. '
                   'Slug of predefined graph in case of predefined-graph.'))

    class Meta:
        ordering = ('index', )

    def __unicode__(self):
        return '%s %s %d' % (
            self.predefined_graph,
            GraphItem.GRAPH_TYPES[self.graph_type], self.index)

    def _require_fewsnorm(self):
        return self.graph_type in [
            GraphItem.GRAPH_TYPE_LINE,
            GraphItem.GRAPH_TYPE_STACKED_BAR,
            GraphItem.GRAPH_TYPE_STACKED_LINE,
            GraphItem.GRAPH_TYPE_STACKED_LINE_CUMULATIVE,
            ]

    def layout_dict(self):
        return self.layout_as_dict()

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
        - polarity (will be mapped to value)
        - value: depends on type
        - layout: dict with optional keys color, color-inside,
          line-width, line-style
        """
        graph_type = GraphItem.GRAPH_TYPES_REVERSE[
            graph_item_dict['type']]
        location = None
        if 'location' in graph_item_dict:
            try:
                location = GeoLocationCache.objects.get(
                    ident=graph_item_dict['location'])
            except GeoLocationCache.DoesNotExist:
                # TODO: see if "db_name" is provided, then add
                # location anyway
                location = GeoLocationCache(
                    ident=graph_item_dict['location'])
                logger.exception(
                    "Ignored not existing GeoLocationCache for ident=%s" %
                    graph_item_dict['location'])

        if graph_type == GraphItem.GRAPH_TYPE_PREDEFINED_GRAPH:
            # This is a special case. Return underlying GraphItems
            try:
                predefined_graph = PredefinedGraph.objects.get(
                    slug=graph_item_dict['value'])
            except PredefinedGraph.DoesNotExist:
                logger.exception("Tried to fetch a non-existing predefined "
                                 "graph %s" % graph_item_dict['value'])
                return []
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
        if 'timestep' in graph_item_dict:
            time_step = TimeStepCache(ident=graph_item_dict['timestep'])
            graph_item.time_step = time_step
        if 'qualifierset' in graph_item_dict:
            qualifier_set = QualifierSetCache(
                ident=graph_item_dict['qualifierset'])
            graph_item.qualifierset = qualifier_set
        if 'polarity' in graph_item_dict:
            graph_item.value = graph_item_dict['polarity']
        if 'value' in graph_item_dict:
            graph_item.value = graph_item_dict['value']
        if 'layout' in graph_item_dict:
            layout_dict = graph_item_dict['layout']
            graph_item.apply_layout_dict(layout_dict)

        return [graph_item, ]

    def as_dict(self):
        """
        Return dictionary form of GraphItem.

        Can be used to recreate GraphItems using from_dict.
        """
        result = {
            'type': GraphItem.GRAPH_TYPES[self.graph_type],
            'layout': self.layout_as_dict(),
            }
        if self.location is not None:
            result['location'] = self.location.ident
        if self.parameter is not None:
            result['parameter'] = self.parameter.ident
        if self.module is not None:
            result['module'] = self.module.ident
        if self.time_step is not None:
            result['timestep'] = self.time_step.ident
        if self.qualifierset is not None:
            result['qualifierset'] = self.qualifierset.ident
        if self.value is not None:
            result['value'] = self.value
        return result


class HorizontalBarGraph(models.Model):
    """
    Predefined horizontal bar graph.
    """
    name = models.CharField(max_length=80)
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
        return '%s (%s)' % (self.name, self.slug)


class HorizontalBarGraphGoal(models.Model):
    """
    Define a goal for a horizontal bar.
    """
    timestamp = models.DateTimeField()
    value = models.FloatField()

    class Meta:
        ordering = ('timestamp', 'value', )

    def __unicode__(self):
        return '%s - %s' % (self.timestamp, self.value)


class HorizontalBarGraphItem(GraphItemMixin):
    """
    Represent one row of a horizontal bar graph.
    """
    horizontal_bar_graph = models.ForeignKey(HorizontalBarGraph)
    index = models.IntegerField(default=100)

    label = models.CharField(
        null=True, blank=True, max_length=80)

    goals = models.ManyToManyField(
        HorizontalBarGraphGoal, null=True, blank=True)

    class Meta:
        # Graphs are drawn on y values in increasing order. The lowest
        # bar is drawn first.
        ordering = ('-index', )

    def __unicode__(self):
        return '%s' % self.label

    @classmethod
    def from_dict(cls, d):
        """
        Return a HorizontalBarGraphItem matching the provided dictionary.

        Note that the objects are not saved.

        The provided dictionary must have the following keys:
        - label: label that you want to show.
        - location: fews location id
        - parameter: fews parameter id
        - module: fews module id
        - goals (optional): list of {'timestamp':<datetime>,
          'value':<floatvalue>}
        """
        try:
            location = GeoLocationCache.objects.get(ident=d['location'])
        except GeoLocationCache.DoesNotExist:
            # TODO: see if "db_name" is provided, then add
            # location anyway
            location = GeoLocationCache(ident=d['location'])
            logger.exception(
                "Ignored not existing GeoLocationCache for ident=%s" %
                d['location'])

        graph_item = HorizotalBarGraphItem()
        graph_item.location = location
        graph_item.parameter = ParameterCache(ident=d['parameter'])
        graph_item.module = ModuleCache(ident=d['module'])
        graph_item.goals = []

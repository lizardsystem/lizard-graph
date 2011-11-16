# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
from django.db import models

from lizard_fewsnorm.models import GeoLocationCache
from lizard_fewsnorm.models import ParameterCache
from lizard_fewsnorm.models import ModuleCache

# Not so pretty. But fewsnorm requires lizard-map anyway, so why not use it?
from lizard_map.models import ColorField


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


class GraphLayout(models.Model):
    """
    Layout that can be applied to a graph entry.

    Options that are used depend on the graph type defined in the
    graph entry.
    """
    color = ColorField(
        null=True, blank=True)
    color_outside = ColorField(
        null=True, blank=True,
        help_text="For stacked-bar, stacked-line and stacked-line-cum")
    line_width = models.FloatField(
        null=True, blank=True, help_text="For everything with lines")
    line_style = models.FloatField(
        null=True, blank=True, help_text="For everything with lines")

    def __unicode__(self):
        return 'GraphLayout'

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
    PERIOD_REVERSE = dict([(b, a) for a, b in PERIOD_CHOICES])

    AGGREGATION_AVG = 1
    AGGREGATION_SUM = 2
    AGGREGATION_CHOICES = (
        (AGGREGATION_AVG, 'avg'),
        (AGGREGATION_SUM, 'sum'),
        )
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
    def fews_norm_db(self):
        return self.location.fews_norm_source.database_name

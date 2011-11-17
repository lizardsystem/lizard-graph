# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
import datetime
import iso8601

from django.http import QueryDict
from django.test import TestCase

from lizard_graph.views import TimeSeriesViewMixin
from lizard_graph.views import GraphView

from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem
from lizard_graph.models import GraphLayout


class TimeSeriesViewMixinTest(TestCase):
    # How to test this one?
    # def test_timeseries_from_graph_item(self):
    #     pass

    def dt_from_request(self, get):
        class MockRequest(object):
            def __init__(self, get):
                self.GET = QueryDict(get)
        request = MockRequest(get)
        timeseries_view_mixin = TimeSeriesViewMixin()
        timeseries_view_mixin.request = request
        result = timeseries_view_mixin._dt_from_request()
        return result

    def test_dt_from_request(self):
        result = self.dt_from_request(
            'dt_start=2011-03-11 00:00:00&dt_end=2011-03-13 00:00:00')
        # Make sure the result is tzoffset aware.
        expected = (iso8601.parse_date('2011-03-11 00:00:00'),
                    iso8601.parse_date('2011-03-13 00:00:00'),)
        self.assertEquals(result, expected)

    def test_dt_from_request2(self):
        result = self.dt_from_request('')
        self.assertTrue(result)
        self.assertTrue(isinstance(result[0], datetime.datetime))
        self.assertTrue(isinstance(result[1], datetime.datetime))

    def test_dt_from_request3(self):
        result = self.dt_from_request(
            'dt_start=2011-03-13 00:00:00&dt_end=2011-03-11 00:00:00')
        # Make sure the result is tzoffset aware.
        expected = (iso8601.parse_date('2011-03-11 00:00:00'),
                    iso8601.parse_date('2011-03-13 00:00:00'),)
        self.assertEquals(result, expected)

    def dimension_from_request(self, get):
        class MockRequest(object):
            def __init__(self, get):
                self.GET = QueryDict(get)
        request = MockRequest(get)
        timeseries_view_mixin = TimeSeriesViewMixin()
        timeseries_view_mixin.request = request
        return timeseries_view_mixin._dimensions_from_request()

    def test_dimensions_from_request(self):
        result = self.dimension_from_request('width=400&height=300')
        expected = (400, 300)
        self.assertEquals(result, expected)

    def test_dimensions_from_request2(self):
        result = self.dimension_from_request('')
        self.assertTrue(result)

    def test_dimensions_from_request3(self):
        result = self.dimension_from_request('width=asdf')
        self.assertTrue(result)


class GraphViewTest(TestCase):
    def graph_items_from_request(self, get):
        class MockRequest(object):
            def __init__(self, get):
                self.GET = QueryDict(get)
        request = MockRequest(get)
        graph_view = GraphView()
        graph_view.request = request
        return graph_view._graph_items_from_request()

    def test_graph_items_from_request(self):
        pg = PredefinedGraph(name='test', slug='test')
        pg.save()
        # Make 2 dummy items
        pg.graphitem_set.create()
        pg.graphitem_set.create()
        result = self.graph_items_from_request('graph=test')

        self.assertEquals(len(result), 2)
        for element in result:
            self.assertTrue(isinstance(element, GraphItem))

    # def test_graph_items_from_request2(self):
    #     pg = PredefinedGraph(name='test', slug='test')
    #     pg.save()
    #     # Make 2 dummy items
    #     pg.graphitem_set.create()
    #     pg.graphitem_set.create()

    #     pg2 = PredefinedGraph(name='test2', slug='test2')
    #     pg2.save()
    #     # Make 1 dummy item
    #     pg2.graphitem_set.create(
    #         graph_type=GraphItem.GRAPH_TYPE_PREDEFINED_GRAPH,
    #         value='test',
    #         )

    #     result = self.graph_items_from_request('graph=test2')

    #     # 2 results: the graph item from pg2 is "unfolded" in graph
    #     # items from pg.
    #     self.assertEquals(len(result), 2)
    #     for element in result:
    #         self.assertTrue(isinstance(element, GraphItem))

    def test_graph_items_from_request3(self):
        result = self.graph_items_from_request(
            'item={"type":"line","location":"111.1","parameter":"ALM",'
            '"layout":{"color":"red"}}')

        self.assertEquals(len(result), 1)


class GraphLayoutTest(TestCase):
    def test_from_dict(self):
        layout_dict = {
            'color': 'ff0000',
            'color-outside': '00ff00',
            'line-width': 3,
            'line-style': '-o'}
        graph_layout = GraphLayout.from_dict(layout_dict)
        self.assertEquals(graph_layout.color, 'ff0000')
        self.assertEquals(graph_layout.color_outside, '00ff00')
        self.assertEquals(graph_layout.line_width, 3)
        self.assertEquals(graph_layout.line_style, '-o')
        self.assertEquals(graph_layout.as_dict(), layout_dict)

    def test_from_dict2(self):
        layout_dict = {
            'color': 'ff0000',
            'line-width': 2}
        graph_layout = GraphLayout.from_dict(layout_dict)
        self.assertEquals(graph_layout.color, 'ff0000')
        self.assertEquals(graph_layout.color_outside, '')
        self.assertEquals(graph_layout.line_width, 2)
        self.assertEquals(graph_layout.line_style, None)
        self.assertEquals(graph_layout.as_dict(), layout_dict)


class GraphItemTest(TestCase):
    def test_from_dict(self):
        graph_item_dict = {
            'type': 'line',
            }
        graph_items = GraphItem.from_dict(graph_item_dict)
        self.assertEquals(len(graph_items), 1)
        self.assertEquals(
            graph_items[0].graph_type, GraphItem.GRAPH_TYPE_LINE)
        self.assertEquals(graph_items[0].as_dict(), graph_item_dict)

    def test_from_dict2(self):
        graph_item_dict = {
            'type': 'line',
            'location': 'fews-location-id',
            'parameter': 'fews-parameter-id',
            'module': 'fews-module-id',
            }
        graph_items = GraphItem.from_dict(graph_item_dict)
        self.assertEquals(len(graph_items), 1)
        self.assertEquals(
            graph_items[0].graph_type, GraphItem.GRAPH_TYPE_LINE)
        self.assertEquals(graph_items[0].as_dict(), graph_item_dict)

    def test_from_dict3(self):
        layout_dict = {'color': '00ff00'}
        graph_item_dict = {
            'type': 'line',
            'location': 'fews-location-id',
            'parameter': 'fews-parameter-id',
            'module': 'fews-module-id',
            'value': 'blabla',
            'period': 'year',
            'aggregation': 'avg',
            'layout': layout_dict,
            }
        graph_items = GraphItem.from_dict(graph_item_dict)
        self.assertEquals(len(graph_items), 1)
        self.assertEquals(
            graph_items[0].graph_type, GraphItem.GRAPH_TYPE_LINE)
        self.assertEquals(
            graph_items[0].location.ident, 'fews-location-id')
        self.assertEquals(
            graph_items[0].parameter.ident, 'fews-parameter-id')
        self.assertEquals(
            graph_items[0].module.ident, 'fews-module-id')
        self.assertEquals(
            graph_items[0].value, 'blabla')
        self.assertEquals(
            graph_items[0].period, GraphItem.PERIOD_YEAR)
        self.assertEquals(
            graph_items[0].aggregation, GraphItem.AGGREGATION_AVG)
        self.assertEquals(
            graph_items[0].layout.as_dict(), layout_dict)
        self.assertEquals(graph_items[0].as_dict(), graph_item_dict)

    def test_from_dict_predefined_graph(self):
        pg = PredefinedGraph(name='test', slug='test-graph')
        pg.save()
        # Make 2 dummy items
        pg.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_LINE,
            value='test-value1',
            index=100)
        pg.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_LINE,
            value='test-value2',
            index=110)

        graph_item_dict = {
            'type': 'predefined-graph',
            'value': 'test-graph'
            }
        graph_items = GraphItem.from_dict(graph_item_dict)
        self.assertEquals(len(graph_items), 2)
        self.assertEquals(
            graph_items[0].graph_type, GraphItem.GRAPH_TYPE_LINE)
        self.assertEquals(graph_items[0].value, 'test-value1')
        self.assertEquals(graph_items[1].value, 'test-value2')

    def test_from_dict_predefined_graph2(self):
        pg = PredefinedGraph(name='test', slug='test-graph')
        pg.save()
        # Make dummy item that contains another predefined graph.
        pg.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_LINE,
            value='line-1', index=100)
        pg.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_PREDEFINED_GRAPH,
            value='test-graph-sub', index=110)

        pg2 = PredefinedGraph(name='test', slug='test-graph-sub')
        pg2.save()
        # Make 2 random dummy items.
        pg2.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_LINE,
            value='sub-1',
            index=100)
        pg2.graphitem_set.create(
            graph_type=GraphItem.GRAPH_TYPE_LINE,
            value='sub-2',
            index=110)

        graph_items = pg.unfolded_graph_items()
        self.assertEquals(len(graph_items), 3)
        self.assertEquals(graph_items[0].value, 'line-1')
        self.assertEquals(graph_items[1].value, 'sub-1')
        self.assertEquals(graph_items[2].value, 'sub-2')

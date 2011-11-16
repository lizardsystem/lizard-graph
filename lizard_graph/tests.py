# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
import datetime
import iso8601

from django.http import QueryDict
from django.test import TestCase

from lizard_graph.views import TimeSeriesViewMixin
from lizard_graph.views import GraphView
from lizard_graph.models import PredefinedGraph
from lizard_graph.models import GraphItem


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

    def test_graph_items_from_request2(self):
        result = self.graph_items_from_request(
            'item={"type":"line","location":"111.1","parameter":"ALM",'
            '"layout":{"color":"red"}}')

        self.assertEquals(len(result), 1)


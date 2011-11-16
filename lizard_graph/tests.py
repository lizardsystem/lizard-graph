# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.
import datetime
import iso8601

from django.test import TestCase

from lizard_graph.views import TimeSeriesViewMixin


class TimeSeriesViewMixinText(TestCase):
    # def test_timeseries_from_graph_item(self):
    #     pass

    def test_dt_from_request(self):
        class MockRequest(object):
            GET = {'dt_start': '2011-03-11 00:00:00',
                   'dt_end': '2011-03-13 00:00:00',}
        request = MockRequest()
        timeseries_view_mixin = TimeSeriesViewMixin()
        timeseries_view_mixin.request = request
        result = timeseries_view_mixin._dt_from_request()
        # Make sure the result is tzoffset aware.
        expected = (iso8601.parse_date('2011-03-11 00:00:00'),
                    iso8601.parse_date('2011-03-13 00:00:00'),)
        self.assertEquals(result, expected)

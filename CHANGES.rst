Changelog of lizard-graph
===================================================


0.24.3 (unreleased)
-------------------

- Nothing changed yet.


0.24.2 (2012-09-25)
-------------------

- Changed url parameter unit-as-y-label to unit_as_y_label.

- Configured setup.py, testsettings.py to run test.


0.24.1 (2012-06-26)
-------------------

- Now really added migration for location_postpend.

- PEP8.


0.24 (2012-06-25)
-----------------

- Added "postpend" option to "find" related locations in a different
  way than the "related location" method.

- Added field GraphItem.location_postpend and migration.


0.23 (2012-06-25)
-----------------

- Added XLS support as format for graph.

- Fixed some PEP8.


0.22 (2012-06-21)
-----------------

- Added format=png_attach, which will return the png as attachment;
  your browser will pick a folder to download the item instead of
  displaying it.

- Added graph html format: table view.


0.21 (2012-06-05)
-----------------

- Nothing changed yet.


0.20 (2012-05-23)
-----------------

- Added output format options: bmp, emf, eps, pdf, ps, raw, rgb, rgba,
  svg, svgz. Existing options were csv and png (default).


0.19 (2012-05-22)
-----------------

- Reordered stacked items so they appear in the same order as the
  legend. Requires nens-graph 0.11.


0.18 (2012-05-22)
-----------------

- Now removes duplicate legend items (uses nens-graph 0.10).


0.17 (2012-04-23)
-----------------

- Added option unit-as-y-label, which can be set to True.


0.16.1 (2012-04-19)
-------------------

- Depend on correct fewsnorm version.


0.16 (2012-04-19)
-----------------

- Made admin for PredefinedGraph faster.

- Implemented related location follower using new fewsnorm.

- Added option to GraphItem to indicate follow a related location.


0.15 (2012-04-16)
-----------------

- Removed unused imports.

- Moved GraphItem.time_series implementation to fewsnorm.


0.14 (2012-04-12)
-----------------

- Upgraded views to work with lizard-fewsnorm 0.13 (still
  experimental).

- Graphs work with timeseries and aggregated timeseries.


0.13 (2012-03-26)
-----------------

- Changed comments of GraphItemMixin.time_series: it's now a string
  instead of a TimeseriesComments object.


0.12 (2012-03-22)
-----------------

- Added a working (but slow) implementation of event comments in
  GraphItemMixin.


0.11 (2012-02-27)
-----------------

- added html page which shows fullscreen graph (/graph/window)


0.10.1 (2012-02-23)
-------------------

- Changed cache keys to make it memcached compatible.


0.10 (2012-02-23)
-----------------

- Added cached_time_series_aggregated to improve performance.

- Added cached_time_series_from_graph_item to improve performance.


0.9 (2012-02-22)
----------------

- Added option for stacked-bar-sign: same as stacked-bar, except that
  it is dependent on the sign where each bar is stacked, on the
  positive side or the negative side.


0.8 (2012-02-09)
----------------

- Added csv output for GraphView.


0.7 (2012-02-08)
----------------

- Fixed stacked bar bug by using nens-graph 0.5.1.

- Moved HorizontalBarGraph view and models to lizard-measure.


0.6 (2012-02-07)
----------------

- Moved DateGridGraph to nens-graph. Now depends on nens-graph >= 0.5.

- Added tests for HorizontalBarGraphView and splitted function.


0.5 (2012-02-06)
----------------

- Added option 'now-line'.

- Added options title and y-label.


0.4 (2012-02-06)
----------------

- Added series selection by time step and qualifier set.


0.3 (2012-02-02)
----------------

- Improved legend locations.

- Added absolute margins around graph.

- Added natural key for predefined graph.

- Implemented options y-range-min and y-range-max of predefined graph.

- Added option for legend-location.


0.2 (2011-12-08)
----------------

- Changed model GraphLayout to an abstract class GraphLayoutMixin. The
  fields are now directly in GraphItem.

- Added url parameter 'location' when using option 'graph'.


0.1.1 (2011-11-28)
------------------

- Removed default GraphLayout.line_width ''.

- Created new initial migration.

Note: If you have old lizard_graph tables, it's best to remove them
first.


0.1 (2011-11-28)
----------------

- Added initial migrations.

- Added test-fixture lizard_graph_test (requires fewsnorm test database).

- Added examples under /graph/examples/.

- Implemented bar graph, with models for predefined graphs.

- Implemented graph types LINE, STACKED_LINE_CUMULATIVE, STACKED_LINE,
  HORIZONTAL_LINE, VERTICAL_LINE, STACKED_BAR.

- Initial models for predefined graphs.

- Initial working line graph, using timeseries, nens-graph and
  lizard-fewsnorm.

- Initial views and urls.py.

- Initial library skeleton created by nensskel.  [Jack Ha]

lizard-graph
==========================================

The goal of this app is to provide various graphs. The app uses
nens-graph as a base for graphs, lizard-fewsnorm as the data source
and the library timeseries for timeseries operations.

All graphs have a grid on the background and the time on the x-axis.

All graph types can be combined in a single graph. You can make a mess
when combining everything, the user must review the usefulness
himself. The graph types that can be produced using this app are
described in the parts below.


Development installation
========================

- Buildout etc.
- Load the test fewsnorm database.
- Make a fewsnorm source.
- Run bin/django sync_fewsnorm on that fewsnorm source. Now the
  GeoLocationCache is filled.
- Run bin/django loaddata lizard_graph_test. It loads a fixture
  corresponding to the test database.
- Run the dev server and go to: /<lizard_graph>/examples/


Graphs
======

The input is the base url, plus url parameters. An example is::

    http://127.0.0.1:8000/graph/?dt_start=2011-02-11%2000:00:00&dt_end=2011-11-11%2000:00:00&item={%22fews_norm_source_slug%22:%22test%22,%22location%22:%22111.1%22,%22parameter%22:%22ALMR110%22,%22type%22:%22line%22}

Standard input is:
- dt_start: datetime start, in iso8601 format.
- dt_end: datetime end, in iso8601 format.
- width: width of output image in pixels.
- height: height of output image in pixels.

- aggregation-period: month*, day, quarter, year (for stacked-bar)
- aggregation: sum*, avg (for stacked-bar)
- reset-period: month*, day, quarter, year (for stacked-line-cumulative)

All parameters can be omitted. For the datetime the session default
will be taken. For the width and height also defaults will be taken.

Labels
- title: default none
- x-label: default none
- y-label: default none


Line
----

The standard graph has one or multiple lines. The values are on the
y-axis. Provide an 'item', each one containing:

- type: line
- location
- parameter
- layout: color, line-width, line-style

Horizontal line
---------------

A static horizontal line that is not linked to a timeseries. An
example application is to display a goal value.

- type: horizontal-line
- value: xxx
- label (optional)
- layout (optional): color, line-width, line-style


Vertical line
---------------

A static vertical line that is not linked to a
timeseries. An example application is to display 'today'.

- type: vertical-line
- value: 'today' or iso8601 date
- label (optional)
- layout (optional): color, line-width, line-style


Stacked bar
-----------

Values are aggregated for certain periods, then displayed as
bars. Color is the bar color. Color-outside is the border color. An
example application is a waterbalance.

- type: stacked-bar
- location
- parameter
- polarity (optional): positive (default), negative
- layout (optional): color, color-outside

Global parameters (outside item):
- aggregation-period: month, day, quarter, year
- aggregation: sum, avg


Stacked line
------------

Values are displayed as lines with will. They are stacked. Color is
the line color. Color-outside is the fill color. An example
application is a fraction distribution.

- type: stacked-line
- location
- parameter
- layout (optional): color, color-outside


Stacked line cumulative
-----------------------

Cumulative values are displayed as lines with fill. The reset period
determines when the cumulative value is reset. Color is
the line color. Color-outside is the fill color. An example application
is rainfall for an area with sub areas.

- type: stacked-line-cum
- location
- parameter
- layout (optional): color, color-outside

Global parameter (outside item):
- reset-period: month, day, quarter, year


Predefined graphs
-----------------

The url for a specific non predefined graph can be very
long. Predefined graphs can be set up and you only need to provide a
few parameters. A predefined graph is 'inserted' as any other graphtype.

This way you can combine multiple predefined graphs in a single
graph. You can even define predefined graphs with other predefined graphs.

The parameters that can be provided:
- type: predefined-graph
- graph: slug of your predefined graph
- location (optional, depends on configuration)
- locations (optional, see below)

Predefined graphs are described with django models without
location. The assumption here is that the same location can be
applied to all parameters that occur in a single graph.

Locations: dictionary with keyword items as keys. Overrides parameter
location and GraphItem.location. For example:

location=naam3
locations={%22loc1%22:%22naam1%22,%22loc2%22:%22naam2%22}

This means:
- loc1 = naam1
- loc2 = naam2
- default location = naam3

To be effective, this requires GraphItems with location_wildcard with
something like:

"%loc1%_1234" -> this becomes "naam1_1234" and will be filled in as
location_id

"%loc3%_asdf" -> loc3 does not exist in the input, so for this
GraphItem it will take the predefined location.

"" -> nothing is filled in in location_wildcard, so for this GraphItem
it will also take the predefined location.

If the predefined location is not filled in, the default location
"naam3" will be used.


Shortcut for predefined graphs
==============================

Most of the time you want to use a single predefined graph. Normally
you would::

    http://127.0.0.1:8000/graph/?dt_start=2011-02-11%2000:00:00&dt_end=2011-11-11%2000:00:00&item={%22type%22:%22predefined-graph%22,%22graph%22:%22test%22,%22location%22:%22111.1%22}&width=500&height=300

Shortcut to do the same::

    http://127.0.0.1:8000/graph/?dt_start=2011-02-11%2000:00:00&dt_end=2011-11-11%2000:00:00&graph=test&location=111.1&width=500&height=300

And you can still use 'item' to add more stuff to your graph.


Horizontal bar graph
====================

Horizontal bar graphs are different from other graphs. On the vertical
axis each item has its own "row". Also, the vertical ticks display the
item name.

- dt_start
- dt_end
- width
- height
- item

Item
----

Each item has:

- label
- location
- parameter
- module
- goal: {year, value} (optional, multiple allowed)

Predefined horizontal bar graph
-------------------------------

- slug
- location (optional)

Provide a slug and optionally a location.

http://127.0.0.1:8000/graph/bar/?dt_start=2011-02-11%2000:00:00&dt_end=2011-11-11%2000:00:00&graph=test&location=111.1&width=500&height=300

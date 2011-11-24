# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'PredefinedGraph'
        db.create_table('lizard_graph_predefinedgraph', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('x_label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('y_label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('y_range_min', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('y_range_max', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('aggregation', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('aggregation_period', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('reset_period', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('lizard_graph', ['PredefinedGraph'])

        # Adding model 'GraphLayout'
        db.create_table('lizard_graph_graphlayout', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('color', self.gf('lizard_map.models.ColorField')(default='', max_length=8, null=True, blank=True)),
            ('color_outside', self.gf('lizard_map.models.ColorField')(default='', max_length=8, null=True, blank=True)),
            ('line_width', self.gf('django.db.models.fields.FloatField')(default='', null=True, blank=True)),
            ('line_style', self.gf('django.db.models.fields.CharField')(default=None, max_length=10, null=True, blank=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
        ))
        db.send_create_signal('lizard_graph', ['GraphLayout'])

        # Adding model 'GraphItem'
        db.create_table('lizard_graph_graphitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.GeoLocationCache'], null=True, blank=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.ParameterCache'], null=True, blank=True)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.ModuleCache'], null=True, blank=True)),
            ('predefined_graph', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_graph.PredefinedGraph'])),
            ('index', self.gf('django.db.models.fields.IntegerField')(default=100)),
            ('graph_type', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True)),
            ('layout', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['lizard_graph.GraphLayout'], null=True, blank=True)),
        ))
        db.send_create_signal('lizard_graph', ['GraphItem'])

        # Adding model 'HorizontalBarGraph'
        db.create_table('lizard_graph_horizontalbargraph', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('x_label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
            ('y_label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
        ))
        db.send_create_signal('lizard_graph', ['HorizontalBarGraph'])

        # Adding model 'HorizontalBarGraphGoal'
        db.create_table('lizard_graph_horizontalbargraphgoal', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('value', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('lizard_graph', ['HorizontalBarGraphGoal'])

        # Adding model 'HorizontalBarGraphItem'
        db.create_table('lizard_graph_horizontalbargraphitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.GeoLocationCache'], null=True, blank=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.ParameterCache'], null=True, blank=True)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_fewsnorm.ModuleCache'], null=True, blank=True)),
            ('horizontal_bar_graph', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['lizard_graph.HorizontalBarGraph'])),
            ('index', self.gf('django.db.models.fields.IntegerField')(default=100)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=80, null=True, blank=True)),
        ))
        db.send_create_signal('lizard_graph', ['HorizontalBarGraphItem'])

        # Adding M2M table for field goals on 'HorizontalBarGraphItem'
        db.create_table('lizard_graph_horizontalbargraphitem_goals', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('horizontalbargraphitem', models.ForeignKey(orm['lizard_graph.horizontalbargraphitem'], null=False)),
            ('horizontalbargraphgoal', models.ForeignKey(orm['lizard_graph.horizontalbargraphgoal'], null=False))
        ))
        db.create_unique('lizard_graph_horizontalbargraphitem_goals', ['horizontalbargraphitem_id', 'horizontalbargraphgoal_id'])


    def backwards(self, orm):
        
        # Deleting model 'PredefinedGraph'
        db.delete_table('lizard_graph_predefinedgraph')

        # Deleting model 'GraphLayout'
        db.delete_table('lizard_graph_graphlayout')

        # Deleting model 'GraphItem'
        db.delete_table('lizard_graph_graphitem')

        # Deleting model 'HorizontalBarGraph'
        db.delete_table('lizard_graph_horizontalbargraph')

        # Deleting model 'HorizontalBarGraphGoal'
        db.delete_table('lizard_graph_horizontalbargraphgoal')

        # Deleting model 'HorizontalBarGraphItem'
        db.delete_table('lizard_graph_horizontalbargraphitem')

        # Removing M2M table for field goals on 'HorizontalBarGraphItem'
        db.delete_table('lizard_graph_horizontalbargraphitem_goals')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lizard_fewsnorm.fewsnormsource': {
            'Meta': {'object_name': 'FewsNormSource'},
            'database_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'lizard_fewsnorm.geolocationcache': {
            'Meta': {'ordering': "('ident', 'name')", 'object_name': 'GeoLocationCache', '_ormbases': ['lizard_geo.GeoObject']},
            'fews_norm_source': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.FewsNormSource']"}),
            'geoobject_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['lizard_geo.GeoObject']", 'unique': 'True', 'primary_key': 'True'}),
            'icon': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'module': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['lizard_fewsnorm.ModuleCache']", 'null': 'True', 'through': "orm['lizard_fewsnorm.TimeSeriesCache']", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parameter': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['lizard_fewsnorm.ParameterCache']", 'null': 'True', 'through': "orm['lizard_fewsnorm.TimeSeriesCache']", 'blank': 'True'}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'timestep': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['lizard_fewsnorm.TimeStepCache']", 'null': 'True', 'through': "orm['lizard_fewsnorm.TimeSeriesCache']", 'blank': 'True'}),
            'tooltip': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'lizard_fewsnorm.modulecache': {
            'Meta': {'ordering': "('ident',)", 'object_name': 'ModuleCache'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'lizard_fewsnorm.parametercache': {
            'Meta': {'ordering': "('ident',)", 'object_name': 'ParameterCache'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'lizard_fewsnorm.timeseriescache': {
            'Meta': {'object_name': 'TimeSeriesCache'},
            'geolocationcache': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.GeoLocationCache']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modulecache': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ModuleCache']"}),
            'parametercache': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ParameterCache']"}),
            'timestepcache': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.TimeStepCache']"})
        },
        'lizard_fewsnorm.timestepcache': {
            'Meta': {'ordering': "('ident',)", 'object_name': 'TimeStepCache'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'lizard_geo.geoobject': {
            'Meta': {'object_name': 'GeoObject'},
            'geo_object_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_geo.GeoObjectGroup']"}),
            'geometry': ('django.contrib.gis.db.models.fields.GeometryField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'})
        },
        'lizard_geo.geoobjectgroup': {
            'Meta': {'object_name': 'GeoObjectGroup'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'source_log': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'lizard_graph.graphitem': {
            'Meta': {'ordering': "('index',)", 'object_name': 'GraphItem'},
            'graph_type': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'default': '100'}),
            'layout': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['lizard_graph.GraphLayout']", 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.GeoLocationCache']", 'null': 'True', 'blank': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ModuleCache']", 'null': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ParameterCache']", 'null': 'True', 'blank': 'True'}),
            'predefined_graph': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_graph.PredefinedGraph']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'})
        },
        'lizard_graph.graphlayout': {
            'Meta': {'object_name': 'GraphLayout'},
            'color': ('lizard_map.models.ColorField', [], {'default': "''", 'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'color_outside': ('lizard_map.models.ColorField', [], {'default': "''", 'max_length': '8', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'line_style': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'line_width': ('django.db.models.fields.FloatField', [], {'default': "''", 'null': 'True', 'blank': 'True'})
        },
        'lizard_graph.horizontalbargraph': {
            'Meta': {'object_name': 'HorizontalBarGraph'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'x_label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'y_label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'})
        },
        'lizard_graph.horizontalbargraphgoal': {
            'Meta': {'ordering': "('timestamp', 'value')", 'object_name': 'HorizontalBarGraphGoal'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'lizard_graph.horizontalbargraphitem': {
            'Meta': {'ordering': "('-index',)", 'object_name': 'HorizontalBarGraphItem'},
            'goals': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['lizard_graph.HorizontalBarGraphGoal']", 'null': 'True', 'blank': 'True'}),
            'horizontal_bar_graph': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_graph.HorizontalBarGraph']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'default': '100'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.GeoLocationCache']", 'null': 'True', 'blank': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ModuleCache']", 'null': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['lizard_fewsnorm.ParameterCache']", 'null': 'True', 'blank': 'True'})
        },
        'lizard_graph.predefinedgraph': {
            'Meta': {'object_name': 'PredefinedGraph'},
            'aggregation': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'aggregation_period': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'reset_period': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'x_label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'y_label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'y_range_max': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'y_range_min': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['lizard_graph']

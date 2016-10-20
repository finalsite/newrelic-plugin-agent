""" varnish """
import logging

from collections import defaultdict
from newrelic_plugin_agent.plugins import base
from newrelic_plugin_agent.commands import varnishstat

LOGGER = logging.getLogger(__name__)

GROUPS = {
  'Backend Traffic':[
    'backend_conn', 'backend_unhealthy', 'backend_busy', 'backend_fail',
    'backend_reuse', 'backend_recycle', 'backend_retry', 'backend_req' ],
  'Backend Health': [
    'backend_unhealthy', 'backend_fail' ],
  'Backend State': [ 
    'backend_conn', 'backend_req', 'backend_fail' ],
  'Cache Utilization':[
    'client_req', 'cache_hit', 'cache_hitpass', 'cache_miss' ],
  'Compression':[ 
    'n_gunzip', 'n_gzip' ],
  'Connections Brief': [
    'backend_conn', 'sess_conn', 'client_req' ],
  'Connections Full':[
    'backend_conn', 'sess_conn', 'sess_drop', 'sess_dropped', 'sess_fail', 'client_req' ],
  'Hit Rates':[ 
    'cache_missrate', 'cache_hitrate', 'cache_passrate' ],
  'Network':[
    's_fetch', 's_synth', 's_pass', 's_pipe', 's_req', 's_sess',
    's_req_bodybytes', 's_req_hdrbytes', 's_resp_bodybytes', 's_resp_hdrbytes',
    's_pipe_hdrbytes', 's_pipe_in', 's_pipe_out' ],
  'Objects':[
    'n_object', 'n_expired', 'n_obj_purged', 'n_objectcore', 
    'n_objecthead', 'n_lru_nuked', 'n_lru_moved' ],
  'Object State': [
    'n_object', 'n_lru_nuked', 'n_expired' ],
  'Response Codes':[ 
    'fetch_1xx', 'fetch_204', 'fetch_304' ],
  'Response Details':[ 
    'fetch_head', 'fetch_length', 'fetch_chunked', 'fetch_none' ],
  'Response Misbehave':[ 
    'fetch_bad', 'fetch_eof', 'fetch_failed', 'fetch_no_thread' ],
  'Sessions':[
    'sess_conn', 'sess_drop', 'sess_fail', 'sess_queued', 'sess_dropped',
    'sess_closed', 'sess_closed_err', 'sess_readahead', 'sess_herd',
    'sc_pipe_overflow' ]
}

UNIT_METRICS = {
  'connections': [
    'backend_busy', 'backend_conn', 'backend_fail', 'backend_recycle', 'backend_req',
    'backend_retry', 'backend_reuse', 'backend_unhealthy', 'sess_conn', 'sess_drop',
    'sess_dropped'
  ],
  'requests': [
    'cache_hit', 'cache_hitpass', 'cache_miss', 'client_req', 'fetch_1xx', 'fetch_204',
    'fetch_304', 'fetch_bad', 'fetch_chunked', 'fetch_eof', 'fetch_failed', 'fetch_head',
    'fetch_length', 'fetch_no_thread', 'fetch_none', 's_fetch', 's_pass', 's_pipe',
    's_pipe_in', 's_pipe_out', 's_req', 's_synth'
  ],
  'objects': [
    'n_expired', 'n_lru_moved', 'n_lru_nuked', 'n_obj_purged', 'n_object',
    'n_objectcore', 'n_objecthead'
  ],
  'operations': [ 
    'n_gunzip', 'n_gzip'
  ],
  'bytes': [
    's_pipe_hdrbytes', 's_req_bodybytes', 's_req_hdrbytes', 's_resp_bodybytes',
    's_resp_hdrbytes'
  ],
  'sessions': [
    's_sess', 'sc_pipe_overflow', 'sess_closed', 'sess_closed_err', 'sess_fail',
    'sess_herd', 'sess_queued', 'sess_readahead'
  ]
}

METRIC_UNITS = defaultdict(lambda: 'unknown', {
  member: unit for (unit, members) in UNIT_METRICS.items() for member in members 
})

def unit(metric_name):
  return METRIC_UNITS[metric_name]

class Varnish(base.JSONStatsCommandPlugin):
    GUID = 'com.finalsite.newrelic_varnish_agent'

    def add_datapoints(self, stats):
      """Add all of the data points for a node

      :param dict stats: all of the nodes

      """
      
      # these have to be done first
      self.add_cache_metric('cache_hit', stats)
      self.add_cache_metric('cache_hitpass', stats)
      self.add_cache_metric('cache_miss', stats)

      for group, components in GROUPS.items():
        for stat in components:
          if not stat in stats: continue

          if stats[stat]['flag'] == 'c':
            method = self.add_derive_value
          elif stats[stat]['flag'] == 'g':
            method = self.add_gauge_value
          
          metric_name = "%s/%s" % (group, stat)
          LOGGER.debug("Reporting: %s[%s] -> %d" % (metric_name, unit(stat), stats[stat]['value']))
          method(metric_name, unit(stat), stats[stat]['value'])
      
    def add_cache_metric(self, metric_name, stats):
        """Process cache statistics

        :param str metric_name: The command metric_name
        :param dict stats: The request stats

        """
        total = self.get_derived_value('Cache Utilization', 'cache_hit', stats) + \
                self.get_derived_value('Cache Utilization', 'cache_miss', stats) + \
                self.get_derived_value('Cache Utilization', 'cache_hitpass', stats)
                
        if total > 0:
            percent = (float(self.get_derived_value('Cache Utilization', metric_name, stats)) / float(total)) * 100
        else:
            percent = 0
            
        LOGGER.debug("Reporting: Hit Percent/%s[percent] -> %.2f" % (metric_name, percent))
        self.add_gauge_value('Hit Percent/%s' % metric_name, 'percent', percent)
    
    def get_derived_value(self, group, metric_name, stats):
      metric = "Component/%s/%s[%s]" % (group, metric_name, unit(metric_name))
      if metric not in self.derive_last_interval.keys():
        return 0.0
      else:
        return stats[metric_name]['value'] - self.derive_last_interval[metric]
        
    def command(self):
      status = varnishstat('-1j', f='MAIN.*')
      status.output = status.output.replace('MAIN.', '')
      return status

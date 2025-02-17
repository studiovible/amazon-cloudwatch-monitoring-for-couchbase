#!/usr/bin/python

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
__author__ = 'John Mousa'

import base64
import json
import sys
import urllib2
import os

cbstats_output_delimiter = "******************************************************************************"


def handler(event):
    auth = create_auth_value(event['username'], event['password'])
    metric_data = []

    cluster_base_url = 'http://{}:{}/'.format('localhost', 8091)

    cluster_monitor_response = get_monitoring_details(cluster_base_url + '/pools/default', auth=auth)
    cluster_name = cluster_monitor_response['clusterName']
    nodes = len(cluster_monitor_response['nodes'])
    healthy_nodes = len([node for node in cluster_monitor_response['nodes'] if 'healthy' == node['status']])

    metric_data.append(create_cluster_metric('HealthyNodes', healthy_nodes, cluster_name, 'None'))
    metric_data.append(create_cluster_metric('NonHealthyNodes', nodes - healthy_nodes, cluster_name, 'None'))

    for node in cluster_monitor_response['nodes']:
        metric_data.append(create_cluster_node_metric(
            'Ops', node['interestingStats']['ops'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))
        metric_data.append(create_cluster_node_metric(
            'Mem_used', node['interestingStats']['mem_used'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))

        metric_data.append(create_cluster_node_metric(
            'Cpu_utilization_rate', node['systemStats']['cpu_utilization_rate'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))

        metric_data.append(create_cluster_node_metric(
            'Mem_free', node['systemStats']['mem_free'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))

        metric_data.append(create_cluster_node_metric(
            'Mem_total', node['systemStats']['mem_total'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))

        metric_data.append(create_cluster_node_metric(
            'Mem_limit', node['systemStats']['mem_limit'],
            cluster_name, node['hostname'], node['nodeUUID'], 'None'))


    if 'buckets' in event:
        buckets = event['buckets']
    else:
        buckets = []

    for bucket in buckets:
        bucket_monitor_response = get_monitoring_details(
            cluster_base_url + '/pools/default/buckets/{}/stats'.format(bucket), auth=auth)
        metric_data.append(
            create_bucket_metric('DiskDrain', bucket_monitor_response['op']['samples']['ep_queue_size'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('KeyCacheMisses', bucket_monitor_response['op']['samples']['ep_cache_miss_rate'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Operations', bucket_monitor_response['op']['samples']['ops'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Gets', bucket_monitor_response['op']['samples']['cmd_get'],
                                 cluster_name, bucket, 'None'))
        metric_data.append(
            create_bucket_metric('Sets', bucket_monitor_response['op']['samples']['cmd_set'],
                                 cluster_name, bucket, 'None'))

    stream = os.popen('docker exec -i {} /opt/couchbase/bin/cbstats localhost all -j -u {} -p {} -a'.format(
        event['container_name'], event['username'], event['password']))
    cbstats_output = stream.read()
    cbstats_lines = cbstats_output.split(cbstats_output_delimiter)

    for cbstats_out_line in cbstats_lines:
        if len(cbstats_out_line) > 0:
            bucket_and_response = cbstats_out_line.split('\n', 1)[1].split('\n', 1)
            bucket = bucket_and_response[0]
            if bucket in buckets:
                bucket_cbstats_response = json.loads(bucket_and_response[1])

    return json.dumps(metric_data)


def create_cluster_metric(metric_name, metric_value, dim_cluster_name, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
        ],
        'Unit': unit,
        'Value': metric_value,
        'StorageResolution': 60,  # This is a low resolution metrics as we have minute granuality data point
    }


def create_cluster_node_metric(metric_name, metric_value,
                               dim_cluster_name, dim_node_hostname, dim_node_id, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
            {
                'Name': 'NodeHostName',
                'Value': dim_node_hostname
            },
            {
                'Name': 'NodeId',
                'Value': dim_node_id
            }
        ],
        'Unit': unit,
        'Value': metric_value,
        'StorageResolution': 60,  # This is a low resolution metrics as we have minute granularity data point
    }


def create_bucket_metric(metric_name, metric_values, dim_cluster_name, dim_bucket, unit):
    return {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'Cluster',
                'Value': dim_cluster_name  # For cluster level metrics we add cluster name as a dimension
            },
            {
                'Name': 'vBucket',
                'Value': dim_bucket  # For bucket level metrics we add bucket name as a dimension
            },
        ],
        'Unit': unit,
        'Values': metric_values,
        'StorageResolution': 1,  # This is a high resolution metrics as we have seconds granuality data point
    }


def create_auth_value(username, password):
    string = '%s:%s' % (username, password)
    return base64.standard_b64encode(string.encode('utf-8'))


def get_monitoring_details(url, auth):
    request = urllib2.Request(
        url=url,
        headers={'Accept': 'application/json'})
    request.add_header("Authorization", "Basic %s" % auth.decode('utf-8'))
    u = urllib2.urlopen(request, timeout=2)
    return json.loads(u.read())


print(handler({'username': sys.argv[1], 'password': sys.argv[2], 'buckets': sys.argv[3].split(','), 'container_name': sys.argv[4]}))
sys.exit(0)

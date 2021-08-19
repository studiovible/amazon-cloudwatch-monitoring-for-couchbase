#!/bin/bash

#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
EC2_AVAIL_ZONE=$(curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
EC2_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"

while getopts ":n:u:p:b:c:" opt; do
  case $opt in
  n)
    namespace="$OPTARG"
    ;;
  u)
    c_username="$OPTARG"
    ;;
  p)
    c_password="$OPTARG"
    ;;
  b)
    buckets="$OPTARG"
    ;;
  c)
    container_name="$OPTARG"
    ;;
  \?)
    echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

DIR="$( cd "$( dirname "$0" )" && pwd -P )"

metric_data=$(python "$DIR"/couchbase_monitor_cli.py "${c_username}" "${c_password}" "${buckets}" "${container_name}" 0>&1)

metric_data1=$(echo $metric_data | jq -c '.[0:20]')
metric_data2=$(echo $metric_data | jq -c '.[20:20]')


aws cloudwatch put-metric-data --namespace "${namespace}" --metric-data "${metric_data1}" --region "${EC2_REGION}"

aws cloudwatch put-metric-data --namespace "${namespace}" --metric-data "${metric_data2}" --region "${EC2_REGION}"

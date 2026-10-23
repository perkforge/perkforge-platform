#!/usr/bin/env bash
set -euo pipefail

region="us-east-1"
stack="perkforge-aws-lab"
local_port="16443"

server_id="$(aws ec2 describe-instances \
  --region "$region" \
  --filters \
    "Name=tag:Project,Values=PerkForgePlatform" \
    "Name=tag:Environment,Values=aws-lab" \
    "Name=tag:LabStack,Values=$stack" \
    "Name=tag:Role,Values=server" \
    "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' \
  --output text)"

if [[ -z "$server_id" || "$server_id" == "None" ]]; then
  echo "No running RKE2 server found for $stack in $region." >&2
  exit 1
fi

exec aws ssm start-session \
  --region "$region" \
  --target "$server_id" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "portNumber=6443,localPortNumber=$local_port"

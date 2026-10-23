# PerkForge AWS lab

Disposable three-node EC2 environment for Ansible and RKE2 development. This
implementation is intentionally isolated from `../` (physical hosts) and
`../../local-lab/` (libvirt VMs). It does not provision EKS or any managed load
balancer.

> **No AWS actions are run by reviewing this directory.** The playbooks below
> create billable resources or delete data. Provision/start/configure/destroy
> require distinct confirmation values; inspect the playbook and current AWS
> profile before running them. Never commit credentials, the generated SSH key,
> kubeconfig, or RKE2 join token.

## Design

- Three `t3a.large` instances in `us-east-1`, one RKE2 server and two agents,
  in one dedicated VPC and one AZ.
- One server is a single-control-plane design. If it fails, the Kubernetes API,
  scheduling, and cluster management are unavailable; this is not HA.
- Nodes use private VPC addresses for cluster traffic. They receive temporary
  public IPv4 addresses for outbound access to OS/RKE2 repositories and AWS
  Systems Manager. Security groups allow no public ingress. The only operator
  path is SSH tunneled through SSM; Kubernetes API access uses an SSM port
  forward. No NAT Gateway, SSM interface endpoints, or public service ingress.
- Instance profile grants the AWS-managed `AmazonSSMManagedInstanceCore` policy.
  Operator credentials come from the local AWS CLI profile/environment; no AWS
  credentials are stored here. Use a dedicated least-privilege profile.
- IMDSv2 is required, EBS is encrypted, CPU credits use `standard`, and the
  root volume has `DeleteOnTermination: true`. Root volumes receive the same
  project/expiry tags as the EC2 instances.
- Teardown deletes the CloudFormation stack (including EC2, VPC, and EBS), the
  EC2 key pair, and local transient key/kubeconfig files. Rebuilds therefore
  start from a clean disk. The pinned AMI ID and Ansible code remain.
- `aws_lab_ami_id`, `aws_lab_os_family`, and `aws_lab_root_device_name` are
  deliberately unset until an OS/AMI is selected. Bottlerocket is not a target
  for this RKE2 host-install workflow. RHEL PAYG incurs a license charge; an
  AWS Linux AMI avoids that charge but needs host/RKE2 compatibility confirmed.

### Cost model

Estimate assumes a 30-day month, two running hours per day (60 instance hours),
50 GiB gp3 root volume per node during each session, three temporary public
IPv4 addresses, and no CPU surplus credits. It excludes taxes and variable
internet egress beyond AWS's shared monthly allowance.

| Component | RHEL PAYG estimate | Amazon Linux estimate |
|---|---:|---:|
| `t3a.large` EC2 compute | $13.54 | $13.54 |
| RHEL software charge | $5.18 | $0.00 |
| 150 GiB gp3 while provisioned (60/730 month) | $0.99 | $0.99 |
| Public IPv4 while running | $0.90 | $0.90 |
| **Estimated total** | **$20.61/month** | **$15.42/month** |

Sources: [T3a pricing and CPU credits](https://aws.amazon.com/ec2/instance-types/t3/),
[RHEL pricing model](https://aws.amazon.com/partners/redhat/rhel-pricing/),
[gp3 pricing](https://aws.amazon.com/ebs/pricing/),
[public IPv4 pricing](https://aws.amazon.com/vpc/pricing/), and
[EC2 data transfer](https://aws.amazon.com/ec2/pricing/on-demand/). Prices can
change and actual charges depend on AMI, usage, tax, and account-level offers.

T3a defaults to Unlimited on AWS. Standard mode is configured here to prevent
surplus-credit charges; sustained CPU above the 30% baseline can be throttled.
If Unlimited is deliberately selected later, Linux surplus credits are priced
at $0.05 per vCPU-hour. Watch `CPUCreditBalance` and `CPUCreditUsage` if changing
the mode. [AWS credit details](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/unlimited-mode-examples.html).

The optional monthly AWS Budget is proposed at $30 with actual 50/80/100% and
forecast 80% alerts. Budget notifications do not stop resources or cap spend.
The budget is account-level and is not removed by lab teardown. Its creation is
a separate, explicitly gated playbook.

## Workstation prerequisites

- Debian workstation with AWS CLI v2, Ansible Core, OpenSSH, and
  `session-manager-plugin`.
- A dedicated AWS CLI profile, preferably IAM Identity Center, selected using
  `AWS_PROFILE`. The profile must be authorized for the limited EC2, VPC,
  CloudFormation, key-pair, SSM session, and scoped IAM pass-role actions
  described below. Do not use account administrator access for routine runs.
- This workstation currently has only a `default` AWS CLI profile using the
  CLI login credential provider. Boto3 compatibility with that provider has not
  been verified; use a profile provider supported by both AWS CLI and Boto3.
- Python `boto3` and `botocore` for Ansible AWS modules. Install the pinned
  collection and Python dependencies in a project virtual environment; do not
  install credentials or dependency artifacts into this directory.
- A selected, pinned AMI ID and root device name in `group_vars/all.yml`.
  Confirm the chosen OS is supported by the pinned RKE2 release before use.
- RKE2 `v1.36.5+rke2r1` is the current inherited pin from the local lab. Update
  it deliberately and keep the server and agent versions identical.

The SSM SSH transport uses `AWS-StartSSHSession`; there is no inbound SSH rule.
The ephemeral EC2 key is created per lab run and stored with mode 0600 under
the repository's ignored `.secrets/aws-lab/credentials/`. The tunnel is
encrypted by SSM; SSH host-key records are kept in that transient directory and
removed on teardown. Assessment evidence is kept separately under
`.secrets/aws-lab/evidence/` and is preserved by teardown.

## Commands

From this directory, after installing dependencies and filling the required
AMI settings (commands shown for later use; **not run as part of this change**):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml

# Each billable/destructive action requires its own exact confirmation.
ansible-playbook playbooks/provision.yml -e aws_lab_confirmation='create perkforge aws lab'
ansible-inventory --graph
ansible-playbook playbooks/configure-hosts.yml -e aws_lab_confirmation='configure perkforge aws lab'
ansible-playbook playbooks/install-rke2.yml -e aws_lab_confirmation='configure perkforge aws lab'
ansible-playbook playbooks/status.yml

# Separate terminal; in another terminal, use the generated kubeconfig.
bash scripts/kubeconfig-tunnel.sh
kubectl --kubeconfig ../../.secrets/aws-lab/credentials/kubeconfig get nodes

ansible-playbook playbooks/stop.yml
ansible-playbook playbooks/start.yml -e aws_lab_confirmation='start perkforge aws lab'
ansible-playbook playbooks/teardown.yml -e aws_lab_confirmation='destroy perkforge aws lab'
```

`provision.yml` creates a CloudFormation stack, including the VPC, security
group, instance role/profile, and three instances. Re-running it with the same
configuration is intended to be idempotent. `start.yml`, `stop.yml`, and
`status.yml` act only on resources tagged for this lab. Teardown is deliberately
destructive and removes disks; re-running it after successful deletion should
be harmless. Review CloudFormation events if a stack fails partway through.

## IAM outline

The EC2 instance role trusts only `ec2.amazonaws.com`, constrained to EC2
instance ARNs in this account and region, and attaches
`AmazonSSMManagedInstanceCore`; it receives no application or cluster
permissions. The operator profile needs the EC2/VPC describe and create/tag
operations needed by the stack, the required `cloudformation:CreateStack`,
`UpdateStack`, `DeleteStack`, and describe/read operations scoped to the lab
stack, `ec2:CreateKeyPair`/`DeleteKeyPair`, and
`ssm:StartSession`/`ssm:TerminateSession` scoped to tagged lab instances and the
SSH/port-forwarding SSM documents. `iam:PassRole` must name only this lab's EC2
role and be constrained to `ec2.amazonaws.com`. IAM role creation/attachment
permissions are needed only for the first stack creation. Budget permissions
are separate. Exact policies must be reviewed against the chosen account and
CloudFormation actions before deployment; this README is not an IAM policy.

## Tenant and security-control test direction

The local platform manifests and Fleet bundles remain the application source of
truth. Once RKE2 is ready, add repeatable checks for synthetic tenant namespace
and RBAC boundaries, network-policy isolation, Fleet target scoping, and
cross-tenant denial. Save timestamped results/findings locally under ignored
`.secrets/aws-lab/evidence/`; publish only sanitized evidence. The initial AWS
playbooks do not claim those controls are implemented or verified.

## Current status

Scaffolding only. No AWS API calls, account changes, provisioning, installation,
or tests have been run by this implementation.

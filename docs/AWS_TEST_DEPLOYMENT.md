# GardenOS Test AWS Deployment

## Goal

Deploy the mowing platform test environment to AWS while keeping all regional runtime resources in New Zealand:

```text
AWS region: ap-southeast-6
Environment: test
Repository: https://github.com/haohan6037/PointCloudT.git
```

## Regional Boundary

Resources that must be created in `ap-southeast-6`:

| Resource | Region requirement | Notes |
| --- | --- | --- |
| ECR repository | `ap-southeast-6` | Stores the application image. |
| ECS cluster / service / task definition | `ap-southeast-6` | Runs the FastAPI app on Fargate. |
| Application Load Balancer | `ap-southeast-6` | Public HTTP test entry. |
| CloudWatch log group | `ap-southeast-6` | Keeps app logs for 14 days by default. |
| Security groups | `ap-southeast-6` | ALB, app task, and app-to-RDS access rule. |
| Secrets Manager secret | `ap-southeast-6` | Existing `Test_DB` secret is reused. |
| PostgreSQL RDS | `ap-southeast-6` | Existing database is reused. |

Resources that cannot be fully regionalized:

| Resource | Why |
| --- | --- |
| IAM roles and policies | IAM is an AWS global control-plane service. |
| GitHub OIDC provider | IAM OIDC provider is global in AWS. |
| GitHub repository and Actions | GitHub is outside AWS. |

This means the application runtime can stay in New Zealand, but identity and CI/CD control-plane resources are not regional resources.

## Existing Resources

| Item | Value |
| --- | --- |
| AWS account ID | `133946907310` |
| AWS region | `ap-southeast-6` |
| VPC ID | `vpc-0ed2b0325e7e44ab0` |
| RDS security group ID | `sg-02416889752ccd804` |
| RDS host | `mygardenostestdb.cno2oku4ynd8.ap-southeast-6.rds.amazonaws.com` |
| RDS port | `5432` |
| RDS database | `postgres` |
| RDS user | `postgres` |
| DB password secret name | `Test_DB` |
| DB password secret ARN | `arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Test_DB-FCSorp` |
| DB password JSON key | `password` |
| Geoapify secret name | `Geoapify` |
| Geoapify secret ARN | `arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Geoapify-2HVDsz` |
| Geoapify JSON key | `GEOAPIFY_API_KEY` |

## Local AWS CLI Blocker

The local machine currently has AWS CLI installed under:

```bash
./.awscli-venv/bin/aws
```

But AWS credentials are not configured. The current error is:

```text
Unable to locate credentials. You can configure credentials by running "aws configure".
```

Until credentials are available, Terraform cannot verify the VPC, subnets, RDS security group, or Secret, and cannot create AWS resources.

## Required Local Credentials

Use one of these methods before running Terraform:

```bash
./.awscli-venv/bin/aws configure
```

or export temporary credentials:

```bash
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..." # only if using temporary credentials
export AWS_DEFAULT_REGION="ap-southeast-6"
```

The IAM identity needs permissions for:

| Area | Needed for |
| --- | --- |
| EC2/VPC/Security Groups | ALB/app security groups and app-to-RDS ingress rule. |
| ECR | Container repository and image push target. |
| ECS/Fargate | Cluster, service, task definition. |
| ELBv2 | Application Load Balancer, target group, listener. |
| CloudWatch Logs | App log group. |
| IAM | ECS task roles and GitHub Actions OIDC role. |
| Secrets Manager read reference | Allow ECS task execution role to read the DB password secret. |

## Terraform

Terraform files live in:

```text
infra/aws/test/
```

The default variables are already set for the provided AWS resources. If the VPC has a specific subnet layout, copy the example variables and set explicit subnet IDs:

```bash
cd infra/aws/test
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Important:

- Do not commit `terraform.tfvars` if it contains private values.
- The stack reuses the existing RDS database; it does not create or delete the database.
- `desired_count` defaults to `1` for low-cost internal testing.
- The app task is configured with `PGSSLMODE=verify-full` and `PGSSLROOTCERT=/app/certs/global-bundle.pem`.
- The existing `Test_DB` secret is JSON. ECS reads `PGPASSWORD` from the `password` key via `SecretARN:password::`.
- The existing `Geoapify` secret is JSON. ECS reads `GEOAPIFY_API_KEY` from the `GEOAPIFY_API_KEY` key via `SecretARN:GEOAPIFY_API_KEY::`.
- If this AWS account already has a GitHub Actions OIDC provider, Terraform may need to import that provider instead of creating a duplicate one.

## GitHub Actions Variables

After Terraform apply, set these GitHub environment variables for the `test` environment:

| Variable | Source |
| --- | --- |
| `AWS_DEPLOY_ROLE_ARN` | Terraform output `github_actions_role_arn` |
| `ECR_REPOSITORY` | Repository name from Terraform output `ecr_repository_url`, without registry prefix |
| `ECS_CLUSTER` | Terraform output `ecs_cluster_name` |
| `ECS_SERVICE` | Terraform output `ecs_service_name` |
| `ECS_TASK_DEFINITION_FAMILY` | Terraform output `ecs_task_family` |
| `CLERK_PUBLIC_KEY` | Clerk dashboard publishable key, if the workflow is extended to render task definitions with runtime env changes |

Deployment workflow:

```text
.github/workflows/deploy-aws-test.yml
```

It builds `mowing-platform/Dockerfile`, pushes the image to ECR, renders a new ECS task definition revision, and updates the ECS service.

## Post-Deployment Resource Table

After deployment, fill this table from Terraform outputs and AWS console:

| Category | Resource | Region | Name / ID | URL / ARN | Stop / cleanup method |
| --- | --- | --- | --- | --- | --- |
| App access | ALB | `ap-southeast-6` | Terraform output `alb_dns_name` | `http://...` | `terraform destroy` |
| Container registry | ECR | `ap-southeast-6` | Terraform output `ecr_repository_url` | ECR repository URL | `terraform destroy` |
| Runtime | ECS cluster | `ap-southeast-6` | Terraform output `ecs_cluster_name` | ECS console | `terraform destroy` |
| Runtime | ECS service | `ap-southeast-6` | Terraform output `ecs_service_name` | ECS console | Set desired count to 0 or `terraform destroy` |
| Logs | CloudWatch log group | `ap-southeast-6` | Terraform output `cloudwatch_log_group` | CloudWatch console | `terraform destroy` |
| Network | ALB SG | `ap-southeast-6` | Terraform output `alb_security_group_id` | EC2 console | `terraform destroy` |
| Network | App SG | `ap-southeast-6` | Terraform output `app_security_group_id` | EC2 console | `terraform destroy` |
| Database | Existing RDS | `ap-southeast-6` | Existing instance | Existing RDS endpoint | Managed separately |
| Secret | Existing `Test_DB` | `ap-southeast-6` | `Test_DB` | Existing secret ARN | Managed separately |
| CI/CD identity | GitHub Actions IAM role | Global IAM | Terraform output `github_actions_role_arn` | IAM role ARN | `terraform destroy` |

## Actual Test Deployment: 2026-06-16

| Category | Resource | Region | Name / ID | URL / ARN | Stop / cleanup method |
| --- | --- | --- | --- | --- | --- |
| App access | Application URL | `ap-southeast-6` | `gardenos-test` | `http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com` | Scale ECS service to 0 or `terraform destroy` |
| App health | Health endpoint | `ap-southeast-6` | `/api/health` | `http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com/api/health` | Same as app access |
| Admin page | Admin portal | `ap-southeast-6` | `/` | `http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com/` | Same as app access |
| Customer page | Customer portal | `ap-southeast-6` | `/customer` | `http://gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com/customer` | Same as app access |
| Container registry | ECR | `ap-southeast-6` | `gardenos-test-app` | `133946907310.dkr.ecr.ap-southeast-6.amazonaws.com/gardenos-test-app` | `terraform destroy` |
| Container image | ECR image | `ap-southeast-6` | `bootstrap` | `sha256:d6458d661a33eac8a80217ed28ac68c8e15e1431b81541150e7a709eea76f0c0` | Delete image or `terraform destroy` |
| Runtime | ECS cluster | `ap-southeast-6` | `gardenos-test` | ECS console | `terraform destroy` |
| Runtime | ECS service | `ap-southeast-6` | `gardenos-test` | Desired `1`, running `1` | Set desired count to `0` or `terraform destroy` |
| Runtime | ECS task definition | `ap-southeast-6` | `gardenos-test:1` | `arn:aws:ecs:ap-southeast-6:133946907310:task-definition/gardenos-test:1` | Deregister unused revisions after cleanup |
| Runtime | ECS container | `ap-southeast-6` | `gardenos-app` | Port `8011` | Same as ECS service |
| Logs | CloudWatch log group | `ap-southeast-6` | `/ecs/gardenos-test` | CloudWatch console | `terraform destroy` |
| Network | ALB | `ap-southeast-6` | `gardenos-test` | `gardenos-test-1275568806.ap-southeast-6.elb.amazonaws.com` | `terraform destroy` |
| Network | ALB security group | `ap-southeast-6` | `sg-06291e4f28d21327f` | EC2 console | `terraform destroy` |
| Network | App security group | `ap-southeast-6` | `sg-0c852148e525cf93f` | EC2 console | `terraform destroy` |
| Network | Public subnets used | `ap-southeast-6` | `subnet-025abbecd471368c5`, `subnet-06d3660bc3f5e2b10` | Existing VPC subnets | Managed separately |
| Database | Existing RDS | `ap-southeast-6` | `mygardenostestdb` | `mygardenostestdb.cno2oku4ynd8.ap-southeast-6.rds.amazonaws.com:5432` | Managed separately |
| Database access | RDS SG ingress rule | `ap-southeast-6` | App SG to `sg-02416889752ccd804:5432` | Security group rule | `terraform destroy` removes app-created rule |
| Secret | Existing `Test_DB` | `ap-southeast-6` | `Test_DB` | `arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Test_DB-FCSorp` | Managed separately |
| CI/CD identity | GitHub OIDC provider | Global IAM | `token.actions.githubusercontent.com` | `arn:aws:iam::133946907310:oidc-provider/token.actions.githubusercontent.com` | `terraform destroy` |
| CI/CD identity | GitHub Actions role | Global IAM | `gardenos-test-github-actions` | `arn:aws:iam::133946907310:role/gardenos-test-github-actions` | `terraform destroy` |

Current verification:

```text
GET /api/health -> {"ok":true,"mode":"postgres","databaseEnabled":true,"error":null}
ECS service -> ACTIVE, desired 1, running 1, pending 0
Target group -> one healthy active target; old replaced target may briefly show draining after deployment
```

Frontend login note:

```text
The admin and customer pages require Clerk_Public_Key in the ECS task environment.
If this value is missing, the app HTML is served but the login shell can appear blank.
```

Fast stop command:

```bash
AWS_DEFAULT_REGION=ap-southeast-6 ./.awscli-venv/bin/aws ecs update-service \
  --region ap-southeast-6 \
  --cluster gardenos-test \
  --service gardenos-test \
  --desired-count 0
```

Full cleanup command:

```bash
AWS_DEFAULT_REGION=ap-southeast-6 /tmp/codex-terraform/terraform \
  -chdir=infra/aws/test destroy
```

## References

- AWS RDS TLS certificate bundle: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
- AWS global RDS bundle URL: https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

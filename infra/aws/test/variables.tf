variable "aws_region" {
  description = "AWS region for all regional runtime resources."
  type        = string
  default     = "ap-southeast-6"

  validation {
    condition     = var.aws_region == "ap-southeast-6"
    error_message = "Test runtime resources must be created in ap-southeast-6 (New Zealand)."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "test"
}

variable "vpc_id" {
  description = "Existing VPC ID in ap-southeast-6."
  type        = string
  default     = "vpc-0ed2b0325e7e44ab0"
}

variable "subnet_ids" {
  description = "Subnets for ALB and Fargate tasks. Leave empty to use all subnets in the VPC."
  type        = list(string)
  default     = []
}

variable "db_security_group_id" {
  description = "Existing RDS security group ID."
  type        = string
  default     = "sg-02416889752ccd804"
}

variable "db_host" {
  description = "Existing RDS PostgreSQL endpoint."
  type        = string
  default     = "mygardenostestdb.cno2oku4ynd8.ap-southeast-6.rds.amazonaws.com"
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "postgres"
}

variable "db_user" {
  description = "PostgreSQL user name."
  type        = string
  default     = "postgres"
}

variable "db_password_secret_value_from" {
  description = "Secrets Manager valueFrom for PGPASSWORD. Use the secret ARN for a plaintext secret, or ARN:json-key:: for JSON."
  type        = string
  default     = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Test_DB-FCSorp:password::"
}

variable "db_password_secret_arn" {
  description = "Base Secrets Manager ARN allowed for ECS task execution."
  type        = string
  default     = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Test_DB-FCSorp"
}

variable "geoapify_api_key_secret_value_from" {
  description = "Secrets Manager valueFrom for GEOAPIFY_API_KEY."
  type        = string
  default     = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Geoapify-2HVDsz:GEOAPIFY_API_KEY::"
}

variable "geoapify_api_key_secret_arn" {
  description = "Base Secrets Manager ARN allowed for Geoapify key access."
  type        = string
  default     = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Geoapify-2HVDsz"
}

variable "clerk_public_key" {
  description = "Clerk publishable key used by the browser login widgets."
  type        = string
  default     = ""
  sensitive   = true
}

variable "clerk_auth_strict" {
  description = "Set to 1 to require verified Clerk Bearer tokens for protected admin/provider APIs."
  type        = string
  default     = "0"

  validation {
    condition     = contains(["0", "1"], var.clerk_auth_strict)
    error_message = "clerk_auth_strict must be either 0 or 1."
  }
}

variable "clerk_issuer" {
  description = "Optional explicit Clerk issuer / Frontend API URL. If empty, it is derived from clerk_public_key."
  type        = string
  default     = ""
}

variable "clerk_authorized_parties" {
  description = "Comma-separated allowed frontend origins for Clerk token azp validation. If empty, the test ALB origin is used."
  type        = string
  default     = ""
}

variable "clerk_jwt_key_secret_value_from" {
  description = "Secrets Manager valueFrom for CLERK_JWT_KEY. Leave empty to omit strict JWT key injection."
  type        = string
  default     = ""
  sensitive   = true
}

variable "clerk_jwt_key_secret_arn" {
  description = "Base Secrets Manager ARN allowed for Clerk JWT public key access."
  type        = string
  default     = "arn:aws:secretsmanager:ap-southeast-6:133946907310:secret:Clerk_JWT_Key-*"
}

variable "admin_emails" {
  description = "Comma-separated emails that should be treated as platform admins."
  type        = string
  default     = "haohan6037@gmail.com,kaiyu.yang@youngproperty.co.nz"
}

variable "provider_emails" {
  description = "Comma-separated emails that should be treated as service providers."
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository in owner/name format."
  type        = string
  default     = "haohan6037/PointCloudT"
}

variable "github_oidc_thumbprint" {
  description = "GitHub Actions OIDC provider thumbprint."
  type        = string
  default     = "6938fd4d98bab03faadb97b34396831e3780aea1"
}

variable "container_port" {
  description = "Application container port."
  type        = number
  default     = 8011
}

variable "desired_count" {
  description = "Number of Fargate tasks for the test environment."
  type        = number
  default     = 1
}

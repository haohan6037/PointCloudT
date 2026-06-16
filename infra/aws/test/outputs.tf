output "aws_region" {
  value = var.aws_region
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "application_url" {
  value = "http://${aws_lb.app.dns_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "ecs_task_family" {
  value = aws_ecs_task_definition.app.family
}

output "ecs_container_name" {
  value = "gardenos-app"
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.app.name
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "alb_dns_name" {
  description = "The permanent public URL for your Application Load Balancer"
  value       = "http://${aws_lb.main.dns_name}"
}
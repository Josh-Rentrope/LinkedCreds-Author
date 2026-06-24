terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ---------------------------------------------------------
# Dynamic Network Lookups (Default VPC)
# ---------------------------------------------------------
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_security_group" "default" {
  vpc_id = data.aws_vpc.default.id
  name   = "default"
}


# ---------------------------------------------------------
# 1. ECR Repositories (Replaces the GitHub Connection)
# ---------------------------------------------------------
resource "aws_ecr_repository" "backend" {
  name                 = "linkedcreds-backend"
  image_tag_mutability = "MUTABLE"
  # force_destroy        = true # Allows TF to destroy the repo even if it has images
}

resource "aws_ecr_repository" "frontend" {
  name                 = "linkedcreds-frontend"
  image_tag_mutability = "MUTABLE"
  # force_destroy        = true
}

# ---------------------------------------------------------
# 2. ECS Cluster
# ---------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "linkedcreds-cluster"
}

# ---------------------------------------------------------
# 3. IAM Roles for ECS Tasks
# ---------------------------------------------------------
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ---------------------------------------------------------
# 4. Backend Service (FastAPI)
# ---------------------------------------------------------
resource "aws_ecs_task_definition" "backend" {
  family                   = "linkedcreds-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024" # 1 vCPU
  memory                   = "2048" # 2 GB
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([{
    name      = "backend-container"
    image     = "${aws_ecr_repository.backend.repository_url}:latest" # Ensure you push an image here!
    essential = true
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
    }]
    environment = [
      { name = "APP_ENV", value = "production" },
      { name = "NEXTAUTH_URL", value = "https://linkedcreds.aws.codingshinobi.org" },
      { name = "NEXTAUTH_SECRET", value = var.nextauth_secret },
      { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "GOOGLE_CLIENT_SECRET", value = var.google_client_secret }
    
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/linkedcreds-backend"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "linkedcreds-backend-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  launch_type     = "FARGATE"
  desired_count   = 1
  
  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend-container" # Must match the container name in your task definition JSON
    container_port   = 8080
  }

  network_configuration {
    subnets          = data.aws_subnets.default.ids
	security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true # Set to false if using NAT Gateway in private subnets
  }
  
  # Note: To expose this to the internet securely, attach a load_balancer block here.
}

# ---------------------------------------------------------
# 5. Frontend Service (Next.js)
# ---------------------------------------------------------
resource "aws_ecs_task_definition" "frontend" {
  family                   = "linkedcreds-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024" # 1 vCPU
  memory                   = "2048" # 2 GB
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn


  container_definitions = jsonencode([{
    name      = "frontend-container"
    image     = "${aws_ecr_repository.frontend.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 3000
      hostPort      = 3000
    }]
    environment = [
      # Note: We use the ALB DNS or an API Gateway URL here instead of the AppRunner URL
      { name = "NEXT_PUBLIC_SKILLS_API_URL", value = "https://linkedcreds.aws.codingshinobi.org/api" },
      { name = "NEXTAUTH_URL", value = "https://linkedcreds.aws.codingshinobi.org" },
      { name = "NEXT_PUBLIC_GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "NEXT_PUBLIC_FIREBASE_API_KEY", value = var.firebase_api_key },
      { name = "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN", value = var.firebase_auth_domain },
      { name = "NEXT_PUBLIC_FIREBASE_PROJECT_ID", value = var.firebase_project_id },
      { name = "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET", value = var.firebase_storage_bucket },
      { name = "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID", value = var.firebase_messaging_sender_id },
      { name = "NEXT_PUBLIC_FIREBASE_APP_ID", value = var.firebase_app_id },
	  { name = "NEXTAUTH_SECRET", value = "put_something_secure_here" },
      { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
      { name = "GOOGLE_CLIENT_SECRET", value = var.google_client_secret }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/linkedcreds-frontend"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "frontend" {
  name            = "linkedcreds-frontend-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend-container" # Must match the container name in your task definition JSON
    container_port   = 3000
  }
  
  network_configuration {
	subnets          = data.aws_subnets.default.ids
	security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  # Note: Attach an Application Load Balancer block here to route internet traffic to port 3000.
}

# ---------------------------------------------------------
# 6. Outputs
# ---------------------------------------------------------
output "ecr_repository_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_repository_frontend_url" {
  value = aws_ecr_repository.frontend.repository_url
}

# ---------------------------------------------------------
# CloudWatch Log Groups for ECS Tasks
# ---------------------------------------------------------
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/linkedcreds-backend"
  retention_in_days = 7 # Automatically purges old logs to keep costs down
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/linkedcreds-frontend"
  retention_in_days = 7
}

# 1. The Application Load Balancer
resource "aws_lb" "main" {
  name               = "linkedcreds-alb"
  internal           = false
  load_balancer_type = "application"

  security_groups = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
}

# 2. Target Group for Frontend (NodeJS Port 3000)
resource "aws_lb_target_group" "frontend" {
  name        = "tg-frontend"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip" # Required for Fargate

  health_check {
    path                = "/"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}

# 3. Target Group for Backend (FastAPI Port 8080)
resource "aws_lb_target_group" "backend" {
  name        = "tg-backend"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip" # Required for Fargate

  health_check {
    path                = "/docs" # FastAPI docs endpoint is a reliable health check
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}


# 4. HTTP Listener (Routes traffic to target groups)
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # Modern secure default
  certificate_arn   = aws_acm_certificate_validation.primary.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener_rule" "nextauth_exception" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 5 # Evaluated first!

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    path_pattern {
      values = ["/api/auth/*", "/api/auth"]
    }
  }
}

# 5. Rule to route "/api/*" traffic to the Backend instead
resource "aws_lb_listener_rule" "api_routing" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/api"]
    }
  }
}

# ---------------------------------------------------------
# Security Groups (Network Firewalls)
# ---------------------------------------------------------

# 1. ALB Security Group: Open to the world
resource "aws_security_group" "alb" {
  name        = "linkedcreds-alb-sg"
  description = "Allow inbound HTTP/HTTPS from the internet"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Allow HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Future-proofing for when you attach your SSL certificate
  ingress {
    description = "Allow HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 2. ECS Tasks Security Group: Locked down to the ALB
resource "aws_security_group" "ecs_tasks" {
  name        = "linkedcreds-ecs-tasks-sg"
  description = "Allow inbound from ALB only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Allow Next.js traffic from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id] # This is the crucial link
  }

  ingress {
    description     = "Allow FastAPI traffic from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound traffic (Required for ECR pulls)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 1. Request the SSL Certificate in AWS Certificate Manager
resource "aws_acm_certificate" "primary" {
  domain_name       = "linkedcreds.aws.codingshinobi.org"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "primary" {
  certificate_arn         = aws_acm_certificate.primary.arn
}

# 1. Request the secondary certificate
resource "aws_acm_certificate" "secondary" {
  domain_name       = "lcdemo.predictiveux.com"
  validation_method = "DNS"
}

# (Perform validation steps for the secondary certificate here, similar to Step 1)

# 2. Attach the new certificate to your existing HTTPS Listener
# resource "aws_lb_listener_certificate" "additional_certs" {
#  listener_arn    = aws_lb_listener.https.arn
#  certificate_arn = aws_acm_certificate.secondary.arn
#}
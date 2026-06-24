terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS provider
# It picks up credentials from your AWS CLI automatically
provider "aws" {
  region = "us-east-1"
}

# Create a simple resource: an S3 bucket (like a cloud folder)
resource "aws_s3_bucket" "my_first_bucket" {
  bucket = "my-unique-bucket-name-klp"
  tags = {
    Name = "MyFirstBucket"
  }
}
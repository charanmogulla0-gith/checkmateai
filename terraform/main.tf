terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  # Swap for S3 backend in a team context:
  # backend "s3" { ... }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "checkmate"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

locals {
  name = "checkmate-${var.environment}"

  # Derived from the current Git SHA at plan time — recorded so every deploy
  # is traceable back to a commit without reading CloudWatch.
  tags_per_service = {
    api    = { Component = "api" }
    worker = { Component = "worker" }
    qdrant = { Component = "vector-store" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

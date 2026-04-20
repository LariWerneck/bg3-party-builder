terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # Estado remoto — descomente após criar o bucket manualmente uma vez
  # backend "s3" {
  #   bucket = "bg3-party-builder-tfstate"
  #   key    = "terraform.tfstate"
  #   region = "us-east-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "bg3-party-builder"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

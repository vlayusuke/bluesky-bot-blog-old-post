# ================================================================================
# Terraform
# ================================================================================
terraform {
  required_version = ">= 1.10.0, < 2.0.0"

  backend "s3" {
    bucket  = "v-bluesky-bot-blog-old-post-terraform-state"
    key     = "state/production.terraform.tfstate"
    region  = "ap-northeast-1"
    profile = "terraform-template"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.42.0"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_elb_service_account" "main" {}
data "aws_region" "current" {}

provider "aws" {
  region  = "ap-northeast-1"
  profile = "terraform-template"

  default_tags {
    tags = {
      Managed    = "terraform"
      Project    = local.project
      Repository = local.repository
      Author     = local.author
    }
  }
}

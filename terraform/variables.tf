variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "dev ou prod"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "bg3-party-builder"
}

variable "alert_email" {
  description = "Email para alertas de custo"
  type        = string
}

variable "github_repo" {
  description = "Repositorio GitHub no formato usuario/repo"
  type        = string
  default     = "LariWerneck/bg3-party-builder"
}

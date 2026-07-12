variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefix for all resources"
  type        = string
  default     = "paris-events"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "AWS key pair name"
  type        = string
  default     = "project-key"
}
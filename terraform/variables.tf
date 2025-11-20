variable "project_id" {}
variable "region" {
  default = "us-central1"
}

variable "prefix" {
  description = "prefix for resource names"
  default     = "covid19"
}

variable "db_user" {
  default = "covid_admin"
}

variable "db_password" {
  default = "covid123"
}

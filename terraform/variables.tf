variable "project" {
  type    = string
}

variable "region" {
  type        = string
  description = "to deploy to"
  default     = "europe-west4"
}

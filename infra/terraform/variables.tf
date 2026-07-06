variable "env" {
  description = "Deployment environment (dev | test | prod)"
  type        = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.env)
    error_message = "env must be one of dev, test, prod."
  }
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Existing resource group to deploy into"
  type        = string
}

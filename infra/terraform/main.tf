locals {
  prefix = "dataops${var.env}"

  tags = {
    workload = "dataops-lakehouse"
    env      = var.env
  }
}

data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "azurerm_storage_account" "lake" {
  name                     = substr(replace("${local.prefix}${random_string.suffix.result}", "-", ""), 0, 24)
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_container" "layers" {
  for_each              = toset(["bronze", "silver", "gold", "quarantine"])
  name                  = each.value
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

resource "azurerm_databricks_workspace" "dbx" {
  name                = "dbw-dataops-${var.env}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.location
  sku                 = "premium"
  tags                = local.tags
}

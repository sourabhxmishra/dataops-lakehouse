@description('Databricks workspace name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@allowed([
  'standard'
  'premium'
])
param skuTier string = 'premium'

var managedRg = 'databricks-rg-${name}-${uniqueString(resourceGroup().id, name)}'

resource dbw 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuTier
  }
  properties: {
    managedResourceGroupId: '${subscription().id}/resourceGroups/${managedRg}'
  }
}

output name string = dbw.name

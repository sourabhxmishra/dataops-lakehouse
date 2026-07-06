targetScope = 'resourceGroup'

@description('Deployment environment')
@allowed([
  'dev'
  'test'
  'prod'
])
param env string

@description('Azure region')
param location string = resourceGroup().location

var prefix = 'dataops${env}'
var tags = {
  workload: 'dataops-lakehouse'
  env: env
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: '${prefix}${uniqueString(resourceGroup().id)}'
    location: location
    tags: tags
  }
}

module dbx 'modules/databricks.bicep' = {
  name: 'databricks'
  params: {
    name: 'dbw-dataops-${env}'
    location: location
    tags: tags
  }
}

output storageName string = storage.outputs.name
output workspaceName string = dbx.outputs.name

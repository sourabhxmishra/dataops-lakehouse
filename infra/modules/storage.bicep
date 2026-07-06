@description('Base name (will be normalized to a valid storage account name)')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  // caller always passes a prefix + uniqueString, so the name is well over 3 chars
  #disable-next-line BCP334
  name: take(toLower(replace(name, '-', '')), 24)
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: sa
  name: 'default'
}

// medallion + a quarantine container for rows that fail the runtime quality gate
resource layers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for c in ['bronze', 'silver', 'gold', 'quarantine']: {
    parent: blob
    name: c
  }
]

output name string = sa.name

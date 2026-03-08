// =====================================================================
// Key Vault Module
// =====================================================================

metadata description = 'Key Vault module for secret management'

param projectName string
param environment string
param location string
param vmManagedIdentityId string
param commonTags object

var uniqueSuffix = uniqueString(resourceGroup().id)
var keyVaultName = 'kv${projectName}${environment}${take(uniqueSuffix, 4)}'

// =====================================================================
// Key Vault
// =====================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: commonTags
  properties: {
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enablePurgeProtection: true
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: vmManagedIdentityId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
          keys: []
          certificates: []
        }
      }
    ]
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// =====================================================================
// Outputs
// =====================================================================

output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUrl string = keyVault.properties.vaultUri

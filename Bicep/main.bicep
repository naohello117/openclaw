// =====================================================================
// Azure AI Agent (OpenClaw) - Main Bicep Template
// Purpose: 熟練Linuxエンジニア育成（AIエージェント化）プロジェクト
// 詳細設計書に基づいたAzureリソースのIaC実装
// =====================================================================

metadata description = 'Azure AI Foundry based AI Agent infrastructure deployment with Bicep'

// =====================================================================
// Parameter Definitions
// =====================================================================

param projectName string = 'aiops'
param environment string = 'prod'
param location string = 'japaneast'
param createdDate string = utcNow('yyyy-MM-dd')

// Network parameters
param vnetAddressSpace string = '10.0.0.0/16'
param mgmtSubnetAddressSpace string = '10.0.1.0/24'
param targetSubnetAddressSpace string = '10.0.2.0/24'

// VM parameters
param vmSize string = 'Standard_B2ms'
param vmOsPublisher string = 'Canonical'
param vmOsOffer string = 'ubuntu-24_04-lts'
param vmOsSku string = 'server'
param vmAdminUsername string = 'azureuser'

// SSH public key (base64 encoded or plain text - provide your key)
@secure()
param sshPublicKey string = ''

// Log Analytics workspace retention
param logAnalyticsRetention int = 30

// =====================================================================
// Variables Definition
// =====================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)
var resourceNamePrefix = '${projectName}-${environment}'

// Resource naming
var vnetName = 'vnet-${resourceNamePrefix}-001'
var mgmtSubnetName = 'snet-mgmt-001'
var targetSubnetName = 'snet-target-001'
var nsgMgmtName = 'nsg-mgmt-001'
var nsgTargetName = 'nsg-target-001'
var vmName = 'vm-openclaw-bastion'
var vmOsDiskName = '${vmName}-osdisk'
var vmNicName = '${vmName}-nic'
var vmDataDiskName = '${vmName}-datadisk'
var vmPublicIpName = '${vmName}-pip'
var keyvaultName = 'kv-${resourceNamePrefix}-${uniqueSuffix}'
var logAnalyticsName = 'log-${resourceNamePrefix}-001'
var aiHubName = 'hub-${resourceNamePrefix}-001'
var storageAccountName = 'st${replace(resourceNamePrefix, '-', '')}${uniqueSuffix}'

// Tags
var commonTags = {
  project: projectName
  environment: environment
  managedBy: 'Bicep'
  createdDate: createdDate
}

// =====================================================================
// 1. Virtual Network & Subnets
// =====================================================================

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: commonTags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressSpace
      ]
    }
    subnets: [
      {
        name: mgmtSubnetName
        properties: {
          addressPrefix: mgmtSubnetAddressSpace
          networkSecurityGroup: {
            id: nsgMgmt.id
          }
          serviceEndpoints: [
            {
              service: 'Microsoft.KeyVault'
            }
            {
              service: 'Microsoft.Storage'
            }
          ]
        }
      }
      {
        name: targetSubnetName
        properties: {
          addressPrefix: targetSubnetAddressSpace
          networkSecurityGroup: {
            id: nsgTarget.id
          }
        }
      }
    ]
  }
}

// =====================================================================
// 2. Network Security Groups (NSG)
// =====================================================================

// Management NSG - for OpenClaw VM
resource nsgMgmt 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: nsgMgmtName
  location: location
  tags: commonTags
  properties: {
    securityRules: [
      {
        name: 'Allow_Inbound_SSH'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: '133.32.181.21'  // Operations team IP address
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
      {
        name: 'Deny_All_Inbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Inbound'
        }
      }
      {
        name: 'Allow_Outbound_Azure'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'AzureCloud'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
        }
      }
    ]
  }
}

// Target NSG - for target Linux VMs
resource nsgTarget 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: nsgTargetName
  location: location
  tags: commonTags
  properties: {
    securityRules: [
      {
        name: 'Allow_SSH_From_OpenClaw'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: mgmtSubnetAddressSpace
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
    ]
  }
}

// =====================================================================
// 3. Public IP for VM
// =====================================================================

resource vmPublicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: vmPublicIpName
  location: location
  tags: commonTags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

// =====================================================================
// 4. Network Interface for VM
// =====================================================================

resource vmNic 'Microsoft.Network/networkInterfaces@2023-11-01' = {
  name: vmNicName
  location: location
  tags: commonTags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: '${vnet.id}/subnets/${mgmtSubnetName}'
          }
          privateIPAllocationMethod: 'Static'
          privateIPAddress: '10.0.1.4'
          publicIPAddress: {
            id: vmPublicIp.id
          }
        }
      }
    ]
    networkSecurityGroup: {
      id: nsgMgmt.id
    }
  }
}

// =====================================================================
// 5. Virtual Machine
// =====================================================================

resource vm 'Microsoft.Compute/virtualMachines@2023-07-01' = {
  name: vmName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    osProfile: {
      computerName: vmName
      adminUsername: vmAdminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${vmAdminUsername}/.ssh/authorized_keys'
              keyData: sshPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: vmOsPublisher
        offer: vmOsOffer
        sku: vmOsSku
        version: 'latest'
      }
      osDisk: {
        name: vmOsDiskName
        caching: 'ReadWrite'
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
        diskSizeGB: 64
      }
      dataDisks: [
        {
          name: vmDataDiskName
          lun: 0
          caching: 'None'
          createOption: 'Empty'
          diskSizeGB: 128
          managedDisk: {
            storageAccountType: 'Standard_LRS'
          }
        }
      ]
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: vmNic.id
          properties: {
            primary: true
          }
        }
      ]
    }
  }
}

// =====================================================================
// 6. Azure Key Vault
// =====================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyvaultName
  location: location
  tags: commonTags
  properties: {
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: vm.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
  }
}

// =====================================================================
// 7. Storage Account (for AI Foundry & Log storage)
// =====================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: commonTags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// =====================================================================
// 8. Log Analytics Workspace
// =====================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-12-01-preview' = {
  name: logAnalyticsName
  location: location
  tags: commonTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: logAnalyticsRetention
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =====================================================================
// 9. Application Insights (optional, linked to Log Analytics)
// =====================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${resourceNamePrefix}-001'
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: logAnalyticsRetention
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =====================================================================
// 10. Cognitive Services Account (base for AI Foundry)
// =====================================================================

resource aiHubAccount 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: aiHubName
  location: location
  tags: commonTags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiHubName
    publicNetworkAccess: 'Enabled'
  }
}

// =====================================================================
// 11. Azure Monitor Action Group (for alerts)
// =====================================================================

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-${resourceNamePrefix}-alerts'
  location: 'global'
  tags: commonTags
  properties: {
    groupShortName: 'AIAlert'
    enabled: true
    emailReceivers: [
      {
        name: 'AdminEmail'
        emailAddress: 'admin@example.com'  // TODO: Replace with actual email
        useCommonAlertSchema: true
      }
    ]
  }
}

// =====================================================================
// Outputs
// =====================================================================

output vnetId string = vnet.id
output vmId string = vm.id
output vmPublicIp string = vmPublicIp.properties.ipAddress
output vmPrivateIp string = vmNic.properties.ipConfigurations[0].properties.privateIPAddress
output keyVaultName string = keyVault.name
output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
output storageAccountName string = storageAccount.name
output aiHubName string = aiHubAccount.name
output vmSystemAssignedManagedIdentity string = vm.identity.principalId

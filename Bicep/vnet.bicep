// =====================================================================
// Network Module - VNet, Subnets, NSG
// =====================================================================

metadata description = 'Network infrastructure module for OpenClaw deployment'

param projectName string
param environment string
param location string
param vnetAddressSpace string
param mgmtSubnetAddressSpace string
param targetSubnetAddressSpace string
param commonTags object

var resourceNamePrefix = '${projectName}-${environment}'
var vnetName = 'vnet-${resourceNamePrefix}-001'
var mgmtSubnetName = 'snet-mgmt-001'
var targetSubnetName = 'snet-target-001'
var nsgMgmtName = 'nsg-mgmt-001'
var nsgTargetName = 'nsg-target-001'

// =====================================================================
// NSG - Management
// =====================================================================

resource nsgMgmt 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: nsgMgmtName
  location: location
  tags: commonTags
  properties: {
    securityRules: [
      // TODO: Slack IP アドレス範囲を確認してから有効化してください
      //{
      //  name: 'Allow_Inbound_Slack_Webhook'
      //  properties: {
      //    protocol: 'Tcp'
      //    sourcePortRange: '*'
      //    destinationPortRange: '443'
      //    sourceAddressPrefix: '199.145.126.0/22'  // Slack IP range (要確認)
      //    destinationAddressPrefix: '*'
      //    access: 'Allow'
      //    priority: 100
      //    direction: 'Inbound'
      //    description: 'Allow inbound from Slack Webhook'
      //  }
      //}
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
          description: 'Allow SSH for maintenance'
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
        name: 'Allow_Outbound_HTTPS'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'AzureCloud'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
          description: 'Allow outbound to Azure services'
        }
      }
    ]
  }
}

// =====================================================================
// NSG - Target
// =====================================================================

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
          description: 'Allow SSH from OpenClaw bastion'
        }
      }
    ]
  }
}

// =====================================================================
// VNet with Subnets
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
// Outputs
// =====================================================================

output vnetId string = vnet.id
output mgmtSubnetId string = '${vnet.id}/subnets/${mgmtSubnetName}'
output targetSubnetId string = '${vnet.id}/subnets/${targetSubnetName}'
output nsgMgmtId string = nsgMgmt.id
output nsgTargetId string = nsgTarget.id

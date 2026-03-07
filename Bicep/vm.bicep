// =====================================================================
// VM Module - Virtual Machine configuration
// =====================================================================

metadata description = 'Virtual Machine module for OpenClaw deployment'

param location string
param vmSize string
param vmAdminUsername string
@secure()
param sshPublicKey string
param subnetId string
param commonTags object

var vmName = 'vm-openclaw-bastion'
var vmNicName = '${vmName}-nic'
var vmOsDiskName = '${vmName}-osdisk'
var vmDataDiskName = '${vmName}-datadisk'
var vmPublicIpName = '${vmName}-pip'

// =====================================================================
// Public IP
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
// Network Interface
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
            id: subnetId
          }
          privateIPAllocationMethod: 'Static'
          privateIPAddress: '10.0.1.4'
          publicIPAddress: {
            id: vmPublicIp.id
          }
        }
      }
    ]
  }
}

// =====================================================================
// Virtual Machine
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
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-noble'
        sku: '24_04-lts-gen2'
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
// Outputs
// =====================================================================

output vmId string = vm.id
output vmName string = vm.name
output vmPublicIp string = vmPublicIp.properties.ipAddress
output vmPrivateIp string = vmNic.properties.ipConfigurations[0].properties.privateIPAddress
output vmSystemAssignedManagedIdentityId string = vm.identity.principalId

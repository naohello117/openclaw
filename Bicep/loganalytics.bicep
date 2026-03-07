// =====================================================================
// Log Analytics Module
// =====================================================================

metadata description = 'Log Analytics workspace module for monitoring'

param projectName string
param environment string
param location string
param retentionInDays int
param commonTags object

var logAnalyticsName = 'log-${projectName}-${environment}-001'

// =====================================================================
// Log Analytics Workspace
// =====================================================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2021-12-01-preview' = {
  name: logAnalyticsName
  location: location
  tags: commonTags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =====================================================================
// Application Insights (linked to Log Analytics)
// =====================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ai-${projectName}-${environment}-001'
  location: location
  tags: commonTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: retentionInDays
    WorkspaceResourceId: logAnalyticsWorkspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =====================================================================
// Outputs
// =====================================================================

output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name
output appInsightsId string = appInsights.id
output appInsightsKey string = appInsights.properties.InstrumentationKey

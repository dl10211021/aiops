import type {
  Asset,
  AssetCategoryDefinition,
  AssetCleanupPlan,
  AssetTypeDefinition,
  AssetVerificationRun,
  ProtocolVerificationOverview,
} from '@/types'
import { request } from './http'

export async function getSavedAssets() {
  return request<{ assets: Asset[] }>('/assets/saved')
}

export async function deleteAsset(assetId: number) {
  return request(`/assets/${assetId}`, { method: 'DELETE' })
}

export async function createAsset(asset: Partial<Asset>) {
  return request('/assets', {
    method: 'POST', body: JSON.stringify(asset),
  })
}

export async function getAsset(assetId: number) {
  return request<{ asset: Asset }>(`/assets/${assetId}`)
}

export async function getAssetVerificationMatrix(assetId: number) {
  return request<{ matrix: ProtocolVerificationOverview['matrix'][number] }>(`/assets/${assetId}/verification`)
}

export async function verifyAsset(assetId: number) {
  return request<{ run: AssetVerificationRun }>(`/assets/${assetId}/verify`, { method: 'POST' })
}

export async function getAssetVerificationRuns(assetId: number, limit = 20) {
  return request<{ runs: AssetVerificationRun[] }>(`/assets/${assetId}/verification/runs?limit=${limit}`)
}

export async function getProtocolVerificationOverview() {
  return request<ProtocolVerificationOverview>('/verification/protocols')
}

export async function getOracleClientConfig() {
  return request<{
    detected: boolean
    lib_dir: string
    source: string
    thick_mode_env_enabled: boolean
  }>('/oracle/client-config')
}

export async function getDatabaseDriverCapabilities() {
  return request<{
    drivers: Record<string, {
      id: string
      label: string
      connector: string
      python_package: string
      python_package_installed: boolean
      external_client_required: boolean
      external_client_detected: boolean
      external_client_name: string
      status: string
      install_hint: string
      recommended_path_windows?: string
      recommended_path_linux?: string
      env_vars?: Record<string, string>
      detected_drivers?: string[]
      test_sql?: string
      test_command?: string
      operation_profile?: {
        id: string
        label: string
        identity_label: string
        default_port: number
        test_statement: string
        readonly_examples: string[]
        write_requires_approval: boolean
        hard_block_examples: string[]
        operator_note: string
      }
      oracle_client?: {
        detected: boolean
        lib_dir: string
        source: string
        thick_mode_env_enabled: boolean
      }
    }>
    oracle_client: {
      detected: boolean
      lib_dir: string
      source: string
      thick_mode_env_enabled: boolean
    }
  }>('/database/driver-capabilities')
}

export async function updateAsset(assetId: number, asset: Partial<Asset>) {
  return request<{ asset: Asset }>(`/assets/${assetId}`, {
    method: 'PUT', body: JSON.stringify(asset),
  })
}

export async function batchImportAssets(items: Partial<Asset>[]) {
  return request('/assets/batch_import', {
    method: 'POST', body: JSON.stringify(items),
  })
}

export async function previewAssetNormalization() {
  return request<AssetCleanupPlan>('/assets/normalize/preview')
}

export async function applyAssetNormalization() {
  return request<{
    backup_path: string
    removed_ids: number[]
    merged_groups: Array<{ keep_id: number; remove_ids: number[]; host: string; port: number }>
    summary: Record<string, unknown>
  }>('/assets/normalize/apply', { method: 'POST' })
}

export async function getAssetTypes() {
  return request<{
    types: AssetTypeDefinition[]
    categories: AssetCategoryDefinition[]
    connector_groups: Array<AssetCategoryDefinition & { tools?: string[] }>
  }>('/assets/types')
}

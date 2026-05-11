import type {
  Asset,
  AssetCategoryDefinition,
  AssetCleanupPlan,
  AssetTypeDefinition,
  ApiResponse,
  AssetVerificationRun,
  ProtocolVerificationOverview,
  ProtocolVerificationStatusOverview,
} from '@/types'
import { request } from './http'

type AssetTypesResponse = {
  types: AssetTypeDefinition[]
  categories: AssetCategoryDefinition[]
  connector_groups: Array<AssetCategoryDefinition & { tools?: string[] }>
}

type DatabaseDriverCapabilitiesResponse = {
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
      thick_mode_default_enabled?: boolean
    }
  }>
  oracle_client: {
    detected: boolean
    lib_dir: string
    source: string
    thick_mode_env_enabled: boolean
    thick_mode_default_enabled?: boolean
  }
}

type CacheOptions = {
  forceRefresh?: boolean
}

type CachedRequest<T> = {
  expiresAt: number
  request: Promise<ApiResponse<T>>
}

const ASSET_CATALOG_CACHE_TTL_MS = 60_000

let assetTypesRequest: CachedRequest<AssetTypesResponse> | null = null
let assetTypeSummaryRequest: CachedRequest<AssetTypesResponse> | null = null
let assetTypeFormCatalogRequest: CachedRequest<AssetTypesResponse> | null = null
let databaseDriverCapabilitiesRequest: CachedRequest<DatabaseDriverCapabilitiesResponse> | null = null

function readCachedRequest<T>(
  cached: CachedRequest<T> | null,
  options: CacheOptions | undefined,
) {
  if (options?.forceRefresh || !cached || cached.expiresAt <= Date.now()) return null
  return cached.request
}

function cacheRequest<T>(
  request: Promise<ApiResponse<T>>,
  onError: () => void,
): CachedRequest<T> {
  return {
    expiresAt: Date.now() + ASSET_CATALOG_CACHE_TTL_MS,
    request: request.catch((error) => {
      onError()
      throw error
    }),
  }
}

function refreshQuery(options: CacheOptions | undefined) {
  return options?.forceRefresh ? '?refresh=true' : ''
}

export function clearAssetCatalogCache() {
  assetTypesRequest = null
  assetTypeSummaryRequest = null
  assetTypeFormCatalogRequest = null
  databaseDriverCapabilitiesRequest = null
}

export async function getSavedAssets() {
  return request<{ assets: Asset[] }>('/assets/saved')
}

export async function deleteAsset(assetId: number) {
  return request(`/assets/${assetId}`, { method: 'DELETE' })
}

export async function bulkDeleteAssets(assetIds: number[]) {
  return request<{ deleted_ids: number[]; deleted: number }>('/assets/delete/bulk', {
    method: 'POST',
    body: JSON.stringify({ asset_ids: assetIds }),
  })
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

export async function getProtocolVerificationStatusOverview() {
  return request<ProtocolVerificationStatusOverview>('/verification/protocols/status')
}

export async function getOracleClientConfig(options?: CacheOptions) {
  return request<{
    detected: boolean
    lib_dir: string
    source: string
    thick_mode_env_enabled: boolean
    thick_mode_default_enabled?: boolean
  }>(`/oracle/client-config${refreshQuery(options)}`)
}

export async function getDatabaseDriverCapabilities(options?: CacheOptions) {
  const cached = readCachedRequest(databaseDriverCapabilitiesRequest, options)
  if (cached) return cached
  databaseDriverCapabilitiesRequest = cacheRequest(
    request<DatabaseDriverCapabilitiesResponse>(`/database/driver-capabilities${refreshQuery(options)}`),
    () => {
      databaseDriverCapabilitiesRequest = null
    },
  )
  return databaseDriverCapabilitiesRequest.request
}

export async function refreshDatabaseDriverCapabilities() {
  databaseDriverCapabilitiesRequest = null
  return getDatabaseDriverCapabilities({ forceRefresh: true })
}

export async function refreshAssetCatalog() {
  assetTypesRequest = null
  assetTypeSummaryRequest = null
  assetTypeFormCatalogRequest = null
  const [types, summary] = await Promise.all([
    getAssetTypes({ forceRefresh: true }),
    getAssetTypeSummary({ forceRefresh: true }),
  ])
  return { types, summary }
}

export async function updateAsset(assetId: number, asset: Partial<Asset>) {
  return request<{ asset: Asset }>(`/assets/${assetId}`, {
    method: 'PUT', body: JSON.stringify(asset),
  })
}

export async function bulkUpdateAssetGroup(assetIds: number[], groupName: string) {
  return request<{ assets: Asset[]; updated: number; group_name: string }>('/assets/groups/bulk', {
    method: 'POST',
    body: JSON.stringify({ asset_ids: assetIds, group_name: groupName }),
  })
}

export async function renameAssetGroup(groupName: string, newGroupName: string) {
  return request<{ assets: Asset[]; updated: number; group_name: string }>('/assets/groups/rename', {
    method: 'POST',
    body: JSON.stringify({ group_name: groupName, new_group_name: newGroupName }),
  })
}

export async function deleteAssetGroup(groupName: string, fallbackGroup = '未分组') {
  return request<{ assets: Asset[]; updated: number; group_name: string; fallback_group: string }>('/assets/groups/delete', {
    method: 'POST',
    body: JSON.stringify({ group_name: groupName, fallback_group: fallbackGroup }),
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

export async function getAssetTypes(options?: CacheOptions) {
  const cached = readCachedRequest(assetTypesRequest, options)
  if (cached) return cached
  assetTypesRequest = cacheRequest(
    request<AssetTypesResponse>('/assets/types'),
    () => {
      assetTypesRequest = null
    },
  )
  return assetTypesRequest.request
}

export async function getAssetTypeSummary(options?: CacheOptions) {
  const cached = readCachedRequest(assetTypeSummaryRequest, options)
  if (cached) return cached
  assetTypeSummaryRequest = cacheRequest(
    request<AssetTypesResponse>('/assets/types/summary'),
    () => {
      assetTypeSummaryRequest = null
    },
  )
  return assetTypeSummaryRequest.request
}

export async function getAssetTypeFormCatalog(options?: CacheOptions) {
  const cached = readCachedRequest(assetTypeFormCatalogRequest, options)
  if (cached) return cached
  assetTypeFormCatalogRequest = cacheRequest(
    request<AssetTypesResponse>('/assets/types/form-catalog'),
    () => {
      assetTypeFormCatalogRequest = null
    },
  )
  return assetTypeFormCatalogRequest.request
}

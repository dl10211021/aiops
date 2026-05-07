import type { AssetParamDefinition, ToolDisplayDetail } from '@/types'

export type AssetCategoryOption = {
  id: string
  label: string
  group?: string
  description?: string
}

export type AssetSubType = {
  id: string
  label: string
  asset_type: string
  defaultPort: number
  authMode?: 'basic' | 'password_only' | 'custom_snmp' | 'none'
  source?: string
  hertzbeat_protocols?: string[]
  params?: AssetParamDefinition[]
  capability?: {
    family: string
    connector: string
    operation_model: string
    tools: string[]
    tool_details?: ToolDisplayDetail[]
    credential_fields?: string[]
    maturity: string
    connector_group?: {
      id: string
      label: string
      group?: string
      tools?: string[]
    }
    parameter_template?: AssetParamDefinition[]
  }
}

export type OracleClientConfig = { detected: boolean; lib_dir: string; source: string; thick_mode_env_enabled: boolean }

export type ConnectionFeedback = {
  ok: boolean
  title: string
  msg: string
  category?: string
}

export type DatabaseDriverCapability = {
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
  oracle_client?: OracleClientConfig
}

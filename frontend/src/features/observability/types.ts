export interface ObservabilitySystem {
  id: string
  name: string
  environment: string
  description?: string
  criticality?: string
  owner?: string
  status?: string
  profile_completeness?: number
  component_count?: number
  unknown_count?: number
  pending_relationship_count?: number
  bound_asset_count?: number
  bound_session_count?: number
  observable_source_count?: number
  created_at?: string
  updated_at?: string
}

export interface ObservabilityComponent {
  id: string
  system_id: string
  name: string
  component_type: string
  workload_family: string
  status?: string
  confidence?: string
  source?: string
  layer?: string
  bound_asset_count?: number
  bound_session_count?: number
  bound_source_count?: number
  metadata?: Record<string, unknown>
}

export interface ObservabilityRelationship {
  id: string
  system_id: string
  from_component_id: string
  to_component_id: string
  relationship_type: string
  confidence?: string
  status?: string
  source?: string
}

export interface ObservabilityTopologyLayer {
  id: string
  label: string
  nodes: ObservabilityComponent[]
}

export interface ObservabilityTopology {
  system_id: string
  layers: ObservabilityTopologyLayer[]
  relationships: ObservabilityRelationship[]
}

export interface ObservableSource {
  id: string
  name: string
  source_type: string
  source_origin?: string
  session_id?: string
  endpoint?: string
  capabilities?: string[]
  status?: string
  last_checked_at?: string
}

export interface ProfilePack {
  id: string
  name: string
  workload_family: string
  version?: string
  component_types?: string[]
  relationship_types?: string[]
}

export interface DiscoveryRun {
  id: string
  system_id: string
  status: string
  summary?: Record<string, unknown>
  review_items?: RelationshipReviewItem[]
}

export interface RelationshipReviewItem {
  id: string
  run_id: string
  system_id: string
  from_component_id: string
  to_component_id: string
  relationship_type: string
  confidence?: string
  status?: string
  evidence?: Array<Record<string, unknown>>
}

export interface Investigation {
  id: string
  system_id: string
  title: string
  symptom: string
  severity?: string
  status?: string
  task_count?: number
  evidence_count?: number
  root_cause_count?: number
  tasks?: InvestigationTask[]
  evidence?: Evidence[]
  root_causes?: RootCauseCandidate[]
  created_at?: string
}

export interface InvestigationTask {
  id: string
  agent_role: string
  task_type: string
  status: string
  target_component_id?: string
  output_summary?: string
}

export interface Evidence {
  id: string
  evidence_type: string
  title: string
  summary: string
  confidence?: string
  timestamp?: string
}

export interface RootCauseCandidate {
  id: string
  title: string
  description: string
  likelihood?: number
  confidence?: string
  status?: string
}


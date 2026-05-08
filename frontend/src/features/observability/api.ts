import { request } from '@/api/http'
import type {
  DiscoveryRun,
  Investigation,
  ObservableSource,
  ObservabilityComponent,
  ObservabilityRelationship,
  ObservabilitySystem,
  ObservabilityTopology,
  ProfilePack,
  RelationshipReviewItem,
} from './types'

export async function listObservabilitySystems() {
  return request<{ systems: ObservabilitySystem[] }>('/observability/systems')
}

export async function createObservabilitySystem(payload: Record<string, unknown>) {
  return request<{ system: ObservabilitySystem }>('/observability/systems', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getObservabilitySystem(systemId: string) {
  return request<{ system: ObservabilitySystem }>(`/observability/systems/${systemId}`)
}

export async function listObservabilityComponents(systemId: string) {
  return request<{ components: ObservabilityComponent[] }>(`/observability/systems/${systemId}/components`)
}

export async function createObservabilityComponent(systemId: string, payload: Record<string, unknown>) {
  return request<{ component: ObservabilityComponent }>(`/observability/systems/${systemId}/components`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createObservabilityRelationship(systemId: string, payload: Record<string, unknown>) {
  return request<{ relationship: ObservabilityRelationship }>(`/observability/systems/${systemId}/relationships`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getObservabilityTopology(systemId: string) {
  return request<{ topology: ObservabilityTopology }>(`/observability/systems/${systemId}/topology`)
}

export async function bindObservabilityAsset(systemId: string, payload: Record<string, unknown>) {
  return request(`/observability/systems/${systemId}/bindings/assets`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function bindObservabilitySession(systemId: string, payload: Record<string, unknown>) {
  return request(`/observability/systems/${systemId}/bindings/sessions`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function listObservableSources() {
  return request<{ sources: ObservableSource[] }>('/observability/sources')
}

export async function createSourceFromSession(payload: Record<string, unknown>) {
  return request<{ source: ObservableSource }>('/observability/sources/from-session', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function checkObservableSource(sourceId: string) {
  return request<{ source: ObservableSource }>(`/observability/sources/${sourceId}/check`, { method: 'POST' })
}

export async function listProfilePacks() {
  return request<{ profile_packs: ProfilePack[] }>('/observability/profile-packs')
}

export async function createDiscoveryRun(systemId: string) {
  return request<{ run: DiscoveryRun }>(`/observability/systems/${systemId}/discovery-runs`, { method: 'POST', body: JSON.stringify({}) })
}

export async function getDiscoveryRun(runId: string) {
  return request<{ run: DiscoveryRun }>(`/observability/discovery-runs/${runId}`)
}

export async function confirmReviewItem(itemId: string) {
  return request<{ review_item: RelationshipReviewItem }>(`/observability/relationship-review-items/${itemId}/confirm`, { method: 'POST' })
}

export async function rejectReviewItem(itemId: string) {
  return request<{ review_item: RelationshipReviewItem }>(`/observability/relationship-review-items/${itemId}/reject`, { method: 'POST' })
}

export async function listInvestigations() {
  return request<{ investigations: Investigation[] }>('/observability/investigations')
}

export async function createInvestigation(payload: Record<string, unknown>) {
  return request<{ investigation: Investigation }>('/observability/investigations', { method: 'POST', body: JSON.stringify(payload) })
}

export async function getInvestigation(investigationId: string) {
  return request<{ investigation: Investigation }>(`/observability/investigations/${investigationId}`)
}

export async function planInvestigation(investigationId: string) {
  return request<{ tasks: Investigation['tasks'] }>(`/observability/investigations/${investigationId}/plan`, { method: 'POST' })
}

export async function dispatchInvestigation(investigationId: string) {
  return request(`/observability/investigations/${investigationId}/dispatch`, { method: 'POST' })
}


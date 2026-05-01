export function policyActionTone(severity?: string) {
  if (severity === 'critical') return 'border-ops-alert/45 bg-ops-alert/10 text-ops-alert'
  if (severity === 'high') return 'border-yellow-300/35 bg-yellow-300/10 text-yellow-100'
  if (severity === 'medium') return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  return 'border-ops-success/30 bg-ops-success/10 text-ops-success'
}

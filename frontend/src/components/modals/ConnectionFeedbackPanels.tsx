import { statusLabel } from '@/utils/assetDisplay'
import type { ConnectionFeedback } from './connectionModalHelpers'

export interface ConnectionInspectionResult {
  ok: boolean
  summary: string
  checks: Array<{ title: string; status: string; output: string }>
}

interface ConnectionFeedbackPanelsProps {
  testResult: ConnectionFeedback | null
  inspectionResult: ConnectionInspectionResult | null
}

export default function ConnectionFeedbackPanels({
  testResult,
  inspectionResult,
}: ConnectionFeedbackPanelsProps) {
  return (
    <>
      {testResult && (
        <div
          className={`rounded-lg border px-3 py-2.5 text-sm ${
            testResult.ok
              ? 'border-ops-success/35 bg-ops-success/10 text-ops-success'
              : 'border-ops-alert/35 bg-ops-alert/10 text-ops-alert'
          }`}
        >
          <div className="font-semibold">{testResult.title}</div>
          <div className="mt-1 text-xs leading-relaxed text-ops-text/85">{testResult.msg}</div>
        </div>
      )}
      {inspectionResult && (
        <div
          className={`rounded-lg p-2 text-xs ${
            inspectionResult.ok
              ? 'bg-ops-success/15 text-ops-success'
              : 'bg-ops-alert/15 text-ops-alert'
          } space-y-2`}
        >
          <div>{inspectionResult.summary}</div>
          {inspectionResult.checks.length > 0 && (
            <div className="max-h-40 space-y-1 overflow-y-auto text-ops-subtext">
              {inspectionResult.checks.map((check) => (
                <div key={check.title} className="rounded bg-ops-dark/60 p-1.5">
                  <div className="font-medium text-ops-text">
                    {statusLabel(check.status)} · {check.title}
                  </div>
                  <pre className="mt-1 whitespace-pre-wrap break-words text-[10px]">
                    {check.output.slice(0, 800)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}

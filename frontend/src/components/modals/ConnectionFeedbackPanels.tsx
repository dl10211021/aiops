import type { ConnectionFeedback } from './connectionModalHelpers'

interface ConnectionFeedbackPanelsProps {
  testResult: ConnectionFeedback | null
}

export default function ConnectionFeedbackPanels({
  testResult,
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
    </>
  )
}

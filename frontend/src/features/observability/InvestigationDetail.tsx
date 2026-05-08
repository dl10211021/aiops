import type { Investigation } from './types'

export default function InvestigationDetail({
  investigation,
  onPlan,
  onDispatch,
}: {
  investigation: Investigation | null
  onPlan: (id: string) => Promise<void>
  onDispatch: (id: string) => Promise<void>
}) {
  if (!investigation) return <div className="ops-data-panel p-5 text-sm text-ops-subtext">请选择排查事件。</div>
  return (
    <div className="ops-data-panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-black text-ops-text">{investigation.title}</h3>
          <p className="mt-1 text-sm text-ops-subtext">{investigation.symptom}</p>
        </div>
        <div className="flex gap-2">
          <button className="ops-control rounded-lg px-3 py-2 text-xs font-semibold" onClick={() => void onPlan(investigation.id)}>生成计划</button>
          <button className="ops-primary-action px-3 py-2 text-xs" onClick={() => void onDispatch(investigation.id)}>调度 Agent</button>
        </div>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <Panel title="Agent 任务">
          {(investigation.tasks || []).map((task) => (
            <div key={task.id} className="rounded bg-ops-surface0/50 px-3 py-2 text-xs">
              <div className="font-semibold text-ops-text">{task.agent_role}</div>
              <div className="mt-1 text-ops-overlay">{task.status} · {task.task_type}</div>
            </div>
          ))}
        </Panel>
        <Panel title="证据">
          {(investigation.evidence || []).map((item) => (
            <div key={item.id} className="rounded bg-ops-surface0/50 px-3 py-2 text-xs">
              <div className="font-semibold text-ops-text">{item.title}</div>
              <div className="mt-1 text-ops-subtext">{item.summary}</div>
            </div>
          ))}
        </Panel>
        <Panel title="根因候选">
          {(investigation.root_causes || []).map((item) => (
            <div key={item.id} className="rounded bg-ops-surface0/50 px-3 py-2 text-xs">
              <div className="font-semibold text-ops-text">{item.title}</div>
              <div className="mt-1 text-ops-subtext">{item.likelihood || 0}% · {item.confidence}</div>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-ops-surface0 bg-ops-dark/20 p-3">
      <h4 className="mb-3 text-sm font-bold text-ops-text">{title}</h4>
      <div className="space-y-2">{children || <div className="py-6 text-center text-xs text-ops-overlay">暂无数据</div>}</div>
    </div>
  )
}


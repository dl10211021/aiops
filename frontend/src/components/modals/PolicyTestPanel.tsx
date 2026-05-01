import type { Dispatch, SetStateAction } from 'react'
import type { SafetyPolicyDecision, SafetyPolicyTestResult } from '@/types'
import { DECISION_LABELS, DEFAULT_TEST_FORM } from './safetyPolicyShared'
import type { CategoryKey, DomainDefinition } from './safetyPolicyShared'

type TestFormState = typeof DEFAULT_TEST_FORM

interface PolicyTestPanelProps {
  activeCategory: CategoryKey
  activeDomain: DomainDefinition
  selectedPlatform: string
  toolName: string
  testForm: TestFormState
  setTestForm: Dispatch<SetStateAction<TestFormState>>
  testing: boolean
  testResult: SafetyPolicyTestResult | null
  runPolicyTest: () => void
  applyTestActionRule: (decision: SafetyPolicyDecision) => void
}

function testResultStyle(decision: string) {
  if (decision === 'allow') return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
  if (decision === 'approval') return 'border-yellow-300/30 bg-yellow-300/10 text-yellow-200'
  return 'border-red-400/30 bg-red-400/10 text-red-200'
}

function actionSeverityStyle(severity?: string) {
  if (severity === 'critical') return 'border-red-400/35 bg-red-400/10 text-red-200'
  if (severity === 'high') return 'border-yellow-300/35 bg-yellow-300/10 text-yellow-200'
  if (severity === 'medium') return 'border-ops-accent/35 bg-ops-accent/10 text-ops-accent'
  return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
}

function policyLayerStyle(matched: boolean, isResolution: boolean) {
  if (isResolution) return 'border-ops-accent bg-ops-accent/12 text-ops-text'
  if (matched) return 'border-yellow-300/30 bg-yellow-300/10 text-yellow-100'
  return 'border-ops-surface0 bg-ops-dark/45 text-ops-subtext'
}

export function PolicyTestPanel({
  activeCategory,
  activeDomain,
  selectedPlatform,
  toolName,
  testForm,
  setTestForm,
  testing,
  testResult,
  runPolicyTest,
  applyTestActionRule,
}: PolicyTestPanelProps) {
  return (
    <section className="mb-4 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-ops-text">规则测试器</h4>
          <p className="mt-1 text-xs text-ops-subtext">只做策略预演，不会连接或执行目标资产。适合保存前检查一条命令会被如何处理。</p>
        </div>
        <span className="rounded-full border border-ops-surface1 px-2 py-1 text-[11px] text-ops-subtext">
          {selectedPlatform} · {testForm.mode === 'readwrite' ? '读写会话' : '只读会话'}
        </span>
      </div>

      <div className="grid grid-cols-[1fr_120px_120px_auto] gap-3">
        <label>
          <span className="text-xs text-ops-subtext">命令 / SQL / API 路径</span>
          <input
            value={testForm.input}
            onChange={(e) => setTestForm({ ...testForm, input: e.target.value })}
            placeholder={activeCategory === 'http' ? '例如 /api/v1/namespaces/prod' : '例如 systemctl restart nginx'}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          />
        </label>
        <label>
          <span className="text-xs text-ops-subtext">HTTP 方法</span>
          <select
            value={testForm.method}
            onChange={(e) => setTestForm({ ...testForm, method: e.target.value })}
            disabled={activeCategory !== 'http'}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent disabled:opacity-45"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="PATCH">PATCH</option>
            <option value="DELETE">DELETE</option>
          </select>
        </label>
        <label>
          <span className="text-xs text-ops-subtext">会话模式</span>
          <select
            value={testForm.mode}
            onChange={(e) => setTestForm({ ...testForm, mode: e.target.value as 'readonly' | 'readwrite' })}
            className="mt-1 w-full rounded-lg border border-ops-surface1 bg-ops-dark px-3 py-2 text-sm text-ops-text outline-none focus:border-ops-accent"
          >
            <option value="readonly">只读</option>
            <option value="readwrite">读写</option>
          </select>
        </label>
        <button
          onClick={runPolicyTest}
          disabled={testing}
          className="mt-5 rounded-lg border border-ops-accent/50 px-4 py-2 text-sm font-medium text-ops-accent transition-colors hover:bg-ops-accent/10 disabled:opacity-45"
        >
          {testing ? '测试中...' : '测试'}
        </button>
      </div>

      {testResult && (
        <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-panel/50 p-3">
          <div className="flex items-center justify-between gap-3">
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${testResultStyle(testResult.decision)}`}>
              {testResult.label}
            </span>
            <div className="flex items-center gap-2">
              {testResult.policy_layers?.find((layer) => layer.id === testResult.resolution_layer) && (
                <span className="rounded-full border border-ops-accent/40 bg-ops-accent/10 px-2 py-0.5 text-[11px] text-ops-accent">
                  生效层级：{testResult.policy_layers.find((layer) => layer.id === testResult.resolution_layer)?.label}
                </span>
              )}
              <span className="font-mono text-[11px] text-ops-overlay">{toolName}</span>
            </div>
          </div>
          <p className="mt-2 text-sm leading-6 text-ops-text">{testResult.reason}</p>
          {testResult.policy_layers?.length ? (
            <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/35 p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div className="text-xs font-semibold text-ops-text">判定优先级</div>
                <div className="text-[11px] text-ops-overlay">从左到右依次判定，命中后按最高优先级生效</div>
              </div>
              <div className="grid gap-2 md:grid-cols-5">
                {testResult.policy_layers
                  .slice()
                  .sort((left, right) => (left.priority || 0) - (right.priority || 0))
                  .map((layer) => {
                    const isResolution = layer.id === testResult.resolution_layer
                    return (
                      <div key={layer.id} className={`rounded-md border px-3 py-2 ${policyLayerStyle(layer.matched, isResolution)}`}>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold">{layer.label}</span>
                          <span className="text-[10px] opacity-75">{isResolution ? '生效' : layer.matched ? '命中' : '未命中'}</span>
                        </div>
                        {layer.reason && <p className="mt-1 text-[11px] leading-4 opacity-85">{layer.reason}</p>}
                      </div>
                    )
                  })}
              </div>
            </div>
          ) : null}
          {(testResult.primary_action || testResult.actions?.[0]) && (
            <div className="mt-3 rounded-lg border border-ops-surface0 bg-ops-dark/45 p-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-semibold text-ops-text">快速转为动作策略</div>
                  <p className="mt-1 text-[11px] text-ops-subtext">
                    将识别到的动作直接写入动作策略，不需要配置命令或正则。
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(['allow', 'approval', 'deny'] as SafetyPolicyDecision[]).map((decision) => (
                    <button
                      key={decision}
                      onClick={() => applyTestActionRule(decision)}
                      className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${DECISION_LABELS[decision].className}`}
                    >
                      设为{DECISION_LABELS[decision].label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {testResult.actions?.length ? (
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {testResult.actions.map((action) => (
                <div key={action.id} className={`rounded-md border px-3 py-2 ${actionSeverityStyle(action.severity)}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold">{action.label}</span>
                    <span className="font-mono text-[10px] opacity-75">{action.id}</span>
                  </div>
                  {action.description && <p className="mt-1 text-[11px] leading-4 opacity-85">{action.description}</p>}
                </div>
              ))}
            </div>
          ) : null}
          <div className="mt-3 grid grid-cols-3 gap-2">
            {testResult.checks.map((check) => (
              <div key={check.name} className="rounded-md border border-ops-surface0 bg-ops-dark/45 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-ops-text">{check.name}</span>
                  <span className={check.matched ? 'text-xs text-yellow-200' : 'text-xs text-ops-overlay'}>
                    {check.matched ? '命中' : '未命中'}
                  </span>
                </div>
                {check.reason && <p className="mt-1 text-[11px] leading-4 text-ops-subtext">{check.reason}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

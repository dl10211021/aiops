import { AdvancedPolicyFields } from './AdvancedPolicyFields'
import { ActionPolicyPanel } from './ActionPolicyPanel'
import { NetworkBoundaryPanel } from './NetworkBoundaryPanel'
import { PolicyRuntimeSettings } from './PolicyRuntimeSettings'
import { PolicyTestPanel } from './PolicyTestPanel'
import {
  SafetyPolicyDecisionGuide,
  SafetyPolicyHeader,
  SafetyPolicySidebar,
} from './SafetyPolicyLayout'
import { resolveToolName } from './safetyPolicyLogic'
import { useSafetyPolicyData } from './useSafetyPolicyData'

export default function SafetyPolicyModal() {
  const {
    activeCategory,
    activeDomain,
    activePanel,
    actionPolicy,
    addCustomActionRule,
    applyTestActionRule,
    boundary,
    category,
    closeModal,
    customActionDomain,
    customActionPlaceholder,
    customActionRows,
    customActionRule,
    policy,
    removeActionRule,
    runPolicyTest,
    save,
    saving,
    selectedPlatform,
    setCustomActionRule,
    setTestForm,
    showActionPanel,
    showAdvancedPanel,
    showNetworkBoundaryPanel,
    showTestPanel,
    switchDomain,
    switchPanel,
    testForm,
    testing,
    testResult,
    totals,
    updateActionRule,
    updateCategory,
    updateNetworkBoundary,
    updatePolicy,
    updateSelectedPlatform,
  } = useSafetyPolicyData()

  return (
    <div className="ops-modal-backdrop" onClick={closeModal}>
      <div
        className="ops-modal-surface flex h-[760px] w-[1180px] max-w-[96vw]"
        onClick={(e) => e.stopPropagation()}
      >
        <SafetyPolicySidebar
          activeDomainId={activeDomain.id}
          policy={policy}
          totals={totals}
          onClose={closeModal}
          onSwitchDomain={switchDomain}
        />

        <main className="flex min-w-0 flex-1 flex-col">
          <SafetyPolicyHeader
            activeDomain={activeDomain}
            activePanel={activePanel}
            selectedPlatform={selectedPlatform}
            onPanelChange={switchPanel}
            onPlatformChange={updateSelectedPlatform}
          />

          {!policy ? (
            <div className="flex flex-1 items-center justify-center text-ops-subtext">加载中...</div>
          ) : (
            <div className="flex-1 overflow-y-auto p-5">
              <SafetyPolicyDecisionGuide />

              {showActionPanel && (
                <ActionPolicyPanel
                  policy={policy}
                  activeDomain={activeDomain}
                  actionPolicy={actionPolicy}
                  customActionDomain={customActionDomain}
                  customActionPlaceholder={customActionPlaceholder}
                  customActionRule={customActionRule}
                  customActionRows={customActionRows}
                  setCustomActionRule={setCustomActionRule}
                  updateActionRule={updateActionRule}
                  removeActionRule={removeActionRule}
                  addCustomActionRule={addCustomActionRule}
                />
              )}

              {showNetworkBoundaryPanel && (
                <NetworkBoundaryPanel
                  boundary={boundary}
                  updateNetworkBoundary={updateNetworkBoundary}
                />
              )}

              {showTestPanel && (
                <PolicyTestPanel
                  activeCategory={activeCategory}
                  activeDomain={activeDomain}
                  selectedPlatform={selectedPlatform}
                  toolName={resolveToolName(activeDomain, selectedPlatform)}
                  testForm={testForm}
                  setTestForm={setTestForm}
                  testing={testing}
                  testResult={testResult}
                  runPolicyTest={runPolicyTest}
                  applyTestActionRule={applyTestActionRule}
                />
              )}

              {showAdvancedPanel && (
                <>
                  <PolicyRuntimeSettings policy={policy} updatePolicy={updatePolicy} />
                  <AdvancedPolicyFields
                    activeCategory={activeCategory}
                    category={category}
                    updateCategory={updateCategory}
                  />
                </>
              )}
            </div>
          )}

          <footer className="ops-modal-footer">
            <button onClick={closeModal} className="ops-control rounded-lg px-4 py-2 text-sm font-semibold">取消</button>
            <button
              onClick={save}
              disabled={!policy || saving}
              className="ops-primary-action px-4 py-2 text-sm disabled:opacity-40"
            >
              {saving ? '保存中...' : '保存策略'}
            </button>
          </footer>
        </main>
      </div>
    </div>
  )
}

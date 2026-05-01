import ConnectionActionBar from './ConnectionActionBar'
import ConnectionAdvancedParamsSection from './ConnectionAdvancedParamsSection'
import ConnectionAssetMetaSection from './ConnectionAssetMetaSection'
import ConnectionAssetTypeSelector from './ConnectionAssetTypeSelector'
import ConnectionCredentialSection from './ConnectionCredentialSection'
import ConnectionDedicatedParamsSection from './ConnectionDedicatedParamsSection'
import ConnectionFeedbackPanels from './ConnectionFeedbackPanels'
import ConnectionScopeSelector from './ConnectionScopeSelector'
import ConnectionPermissionSection from './ConnectionPermissionSection'
import ConnectionSkillsSelector from './ConnectionSkillsSelector'
import { useConnectionModalController } from './useConnectionModalController'

export default function ConnectionModal() {
  const {
    assetCategories,
    assetTypeSearch,
    oracleClientConfig,
    oracleThickDefaults,
    skills,
    authVisibility,
    canSubmitAsset,
    categoryGroups,
    closeModal,
    connecting,
    currentProtocol,
    databaseDriverInfo,
    extensionParamGroups,
    filteredSubTypeOptions,
    form,
    handleCategoryChange,
    handleConnect,
    handleInspect,
    handleSaveOnly,
    handleSubTypeChange,
    handleTest,
    inferredHostFromEndpoint,
    inspecting,
    inspectionResult,
    isEndpointBackedAsset,
    isKubernetesAsset,
    normalizedAssetTypeSearch,
    searchedSubTypeOptions,
    selectedConnectionHint,
    selectedConnectorGroup,
    selectedConnectorLabel,
    selectedMaturity,
    selectedSkills,
    selectedSubInfo,
    selectedTools,
    setAssetTypeSearch,
    setExtraArg,
    setExtraArgs,
    setForm,
    setSkillSearch,
    shouldShowGenericHttpParams,
    skillSearch,
    subTypeGroups,
    subTypeOptions,
    testing,
    testResult,
    toggleSkill,
  } = useConnectionModalController()

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center">
      <div className="flex max-h-[94vh] w-[860px] max-w-[94vw] flex-col rounded-lg border border-ops-surface0 bg-ops-panel shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-ops-surface0 px-6 py-4">
          <div>
            <h2 className="text-lg font-bold text-ops-text">新建连接</h2>
            <p className="mt-0.5 text-xs text-ops-subtext">选择资产类型后，系统会自动匹配协议、连接器和可用工具。</p>
          </div>
          <button onClick={closeModal} className="text-ops-subtext hover:text-ops-text text-sm">关闭</button>
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-4 pb-6">
          <ConnectionScopeSelector
            value={form.target_scope}
            onChange={(targetScope) => setForm({ ...form, target_scope: targetScope })}
          />

          {form.target_scope !== 'global' && (
            <ConnectionAssetTypeSelector
              assetCategories={assetCategories}
              assetTypeSearch={assetTypeSearch}
              category={form.category}
              categoryGroups={categoryGroups}
              currentProtocol={currentProtocol}
              filteredSubTypeOptions={filteredSubTypeOptions}
              normalizedAssetTypeSearch={normalizedAssetTypeSearch}
              searchedSubTypeOptions={searchedSubTypeOptions}
              selectedConnectionHint={selectedConnectionHint}
              selectedConnectorGroup={selectedConnectorGroup}
              selectedConnectorLabel={selectedConnectorLabel}
              selectedMaturity={selectedMaturity}
              selectedSubInfo={selectedSubInfo}
              selectedTools={selectedTools}
              subType={form.sub_type}
              subTypeGroups={subTypeGroups}
              subTypeOptions={subTypeOptions}
              onCategoryChange={handleCategoryChange}
              onSearchChange={setAssetTypeSearch}
              onSubTypeChange={handleSubTypeChange}
            />
          )}

          {form.target_scope !== 'global' && (
            <ConnectionCredentialSection
              host={form.host}
              inferredHostFromEndpoint={inferredHostFromEndpoint}
              isEndpointBackedAsset={isEndpointBackedAsset}
              password={form.password}
              port={form.port}
              showPass={authVisibility.showPass}
              showUser={authVisibility.showUser}
              targetScope={form.target_scope}
              username={form.username}
              onHostChange={(host) => setForm({ ...form, host })}
              onPasswordChange={(password) => setForm({ ...form, password })}
              onPortChange={(port) => setForm({ ...form, port })}
              onUsernameChange={(username) => setForm({ ...form, username })}
            />
          )}

          <ConnectionAssetMetaSection
            groupName={form.group_name}
            remark={form.remark}
            onGroupNameChange={(group_name) => setForm({ ...form, group_name })}
            onRemarkChange={(remark) => setForm({ ...form, remark })}
          />

          {/* Custom Extra Fields */}
          {form.target_scope !== 'global' && (
            <div className="space-y-3">
              <ConnectionDedicatedParamsSection
                category={form.category}
                currentProtocol={currentProtocol}
                databaseDriverInfo={databaseDriverInfo}
                extraArgs={form.extra_args}
                isKubernetesAsset={isKubernetesAsset}
                oracleClientConfig={oracleClientConfig}
                port={form.port}
                selectedConnectorLabel={selectedConnectorLabel}
                shouldShowGenericHttpParams={shouldShowGenericHttpParams}
                subType={form.sub_type}
                onExtraArgChange={setExtraArg}
                onExtraArgsChange={setExtraArgs}
                oracleThickDefaults={() => oracleThickDefaults()}
              />

              <ConnectionAdvancedParamsSection
                connectorLabel={selectedSubInfo?.capability?.connector_group?.label || selectedSubInfo?.capability?.connector}
                extraArgs={form.extra_args}
                maturity={selectedSubInfo?.capability?.maturity}
                paramGroups={extensionParamGroups}
                onParamChange={setExtraArg}
              />
            </div>
          )}

          <ConnectionSkillsSelector
            search={skillSearch}
            selectedSkills={selectedSkills}
            skills={skills}
            onSearchChange={setSkillSearch}
            onToggleSkill={toggleSkill}
          />

          <ConnectionPermissionSection
            allowModifications={form.allow_modifications}
            onChange={(allowModifications) => setForm({ ...form, allow_modifications: allowModifications })}
          />

          <ConnectionFeedbackPanels testResult={testResult} inspectionResult={inspectionResult} />
        </div>

        <ConnectionActionBar
          canSubmitAsset={canSubmitAsset}
          connecting={connecting}
          inspecting={inspecting}
          testing={testing}
          onConnect={handleConnect}
          onInspect={handleInspect}
          onSaveOnly={handleSaveOnly}
          onTest={handleTest}
        />
      </div>
    </div>
  )
}

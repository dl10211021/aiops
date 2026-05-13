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
    assetCatalogMode,
    assetTypeSearch,
    accessProtocolOptions,
    oracleClientConfig,
    oracleThickDefaults,
    skills,
    authVisibility,
    canSubmitAsset,
    catalogStatus,
    categoryGroups,
    closeModal,
    connecting,
    currentProtocol,
    currentAccessProtocol,
    databaseDriverInfo,
    extensionParamGroups,
    filteredSubTypeOptions,
    form,
    handleCategoryChange,
    handleConnect,
    handleProtocolChange,
    handleSaveOnly,
    handleSubTypeChange,
    handleTest,
    inferredHostFromEndpoint,
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
    selectedToolDetails,
    selectedTools,
    setAssetCatalogMode,
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
    <div className="ops-modal-backdrop">
      <div className="ops-modal-surface flex max-h-[94vh] w-[860px] max-w-[94vw] flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="ops-modal-header">
          <div>
            <h2 className="ops-modal-title">
              {typeof window !== 'undefined' && window.sessionStorage.getItem('asset_editing_id') ? '编辑资产' : '新建连接'}
            </h2>
            <p className="ops-modal-description">选择数据中心常规资产类型后，平台会带出最适合 AI 登录、查询和操作的主接入方式；巡检请在会话快捷指令中触发。</p>
          </div>
          <button onClick={closeModal} className="ops-icon-button" title="关闭">×</button>
        </div>

        <div className="ops-modal-body space-y-4 px-6 py-4 pb-6">
          <ConnectionScopeSelector
            value={form.target_scope}
            onChange={(targetScope) => setForm({ ...form, target_scope: targetScope })}
          />

          {form.target_scope !== 'global' && (
            <ConnectionAssetTypeSelector
              assetCategories={assetCategories}
              assetCatalogMode={assetCatalogMode}
              assetTypeSearch={assetTypeSearch}
              catalogStatus={catalogStatus}
              category={form.category}
              categoryGroups={categoryGroups}
              currentAccessProtocol={currentAccessProtocol}
              currentProtocol={currentProtocol}
              accessProtocolOptions={accessProtocolOptions}
              filteredSubTypeOptions={filteredSubTypeOptions}
              normalizedAssetTypeSearch={normalizedAssetTypeSearch}
              searchedSubTypeOptions={searchedSubTypeOptions}
              selectedConnectionHint={selectedConnectionHint}
              selectedConnectorGroup={selectedConnectorGroup}
              selectedConnectorLabel={selectedConnectorLabel}
              selectedMaturity={selectedMaturity}
              selectedSubInfo={selectedSubInfo}
              selectedToolDetails={selectedToolDetails}
              selectedTools={selectedTools}
              subType={form.sub_type}
              subTypeGroups={subTypeGroups}
              subTypeOptions={subTypeOptions}
              onCategoryChange={handleCategoryChange}
              onCatalogModeChange={setAssetCatalogMode}
              onProtocolChange={handleProtocolChange}
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

          <ConnectionFeedbackPanels testResult={testResult} />
        </div>

        <ConnectionActionBar
          canSubmitAsset={canSubmitAsset}
          connecting={connecting}
          testing={testing}
          onConnect={handleConnect}
          onSaveOnly={handleSaveOnly}
          onTest={handleTest}
        />
      </div>
    </div>
  )
}

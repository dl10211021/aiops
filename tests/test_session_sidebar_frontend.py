from pathlib import Path


def test_session_group_header_exposes_bulk_permission_actions():
    group_list = Path("frontend/src/features/sessions/SessionGroupList.tsx").read_text(encoding="utf-8")
    sidebar = Path("frontend/src/features/sessions/SessionSidebar.tsx").read_text(encoding="utf-8")
    model = Path("frontend/src/features/sessions/useSessionSidebarModel.ts").read_text(encoding="utf-8")

    assert "onSetGroupPermission: (group: string, allowModifications: boolean) => void" in group_list
    assert "全组只读" in group_list
    assert "全组读写" in group_list
    assert "onClick={() => onSetGroupPermission(group, false)}" in group_list
    assert "onClick={() => onSetGroupPermission(group, true)}" in group_list
    assert "onSetGroupPermission={model.handleSetGroupPermission}" in sidebar
    assert "handleSetGroupPermission" in model
    assert "syncSessionsPermissionToBackend(affected, allowModifications, updateSession, addToast, 'group', currentName)" in model


def test_session_sidebar_exposes_global_permission_actions():
    sidebar = Path("frontend/src/features/sessions/SessionSidebar.tsx").read_text(encoding="utf-8")
    model = Path("frontend/src/features/sessions/useSessionSidebarModel.ts").read_text(encoding="utf-8")

    assert "全部只读" in sidebar
    assert "全部读写" in sidebar
    assert "model.handleSetAllSessionsPermission(false)" in sidebar
    assert "model.handleSetAllSessionsPermission(true)" in sidebar
    assert "handleSetAllSessionsPermission" in model
    assert "syncSessionsPermissionToBackend(sessionList, allowModifications, updateSession, addToast, 'global')" in model
    assert "暂无活跃会话" in model


def test_session_group_bulk_permission_sync_is_optimistic_and_rolls_back_failures():
    effects = Path("frontend/src/features/sessions/sessionSidebarEffects.ts").read_text(encoding="utf-8")

    assert "export async function syncSessionsPermissionToBackend" in effects
    assert "items.filter((session) => session.isReadWriteMode !== allowModifications)" in effects
    assert "updateSession(session.id, { isReadWriteMode: allowModifications })" in effects
    assert "syncMultiAgentPermissions({" in effects
    assert "permission_mode: allowModifications ? 'readwrite' : 'readonly'" in effects
    assert "target_session_ids: changed.map((session) => session.id)" in effects
    assert "已同步 ${response.data.target_count} 个会话，跳过 ${response.data.skipped_count} 个" in effects
    assert "updatePermission(session.id, allowModifications)" in effects
    assert "updateSession(item.session.id, { isReadWriteMode: item.session.isReadWriteMode })" in effects
    assert "部分会话权限同步失败，已回退失败项" in effects


def test_session_connection_exposes_multi_agent_permission_sync_api():
    api = Path("frontend/src/api/sessionConnection.ts").read_text(encoding="utf-8")

    assert "export async function syncMultiAgentPermissions" in api
    assert "scope: 'global' | 'group'" in api
    assert "permission_mode: 'readonly' | 'readwrite'" in api
    assert "target_session_ids?: string[]" in api
    assert "'/sessions/multi-agent/permissions'" in api

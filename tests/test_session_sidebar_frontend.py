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
    assert "syncSessionsPermissionToBackend(affected, allowModifications, updateSession, addToast)" in model


def test_session_group_bulk_permission_sync_is_optimistic_and_rolls_back_failures():
    effects = Path("frontend/src/features/sessions/sessionSidebarEffects.ts").read_text(encoding="utf-8")

    assert "export async function syncSessionsPermissionToBackend" in effects
    assert "items.filter((session) => session.isReadWriteMode !== allowModifications)" in effects
    assert "updateSession(session.id, { isReadWriteMode: allowModifications })" in effects
    assert "updatePermission(session.id, allowModifications)" in effects
    assert "updateSession(item.session.id, { isReadWriteMode: item.session.isReadWriteMode })" in effects
    assert "部分会话权限同步失败，已回退失败项" in effects

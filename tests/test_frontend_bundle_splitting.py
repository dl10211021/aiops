from pathlib import Path


def test_vite_config_splits_large_vendor_chunks():
    source = Path("frontend/vite.config.ts").read_text(encoding="utf-8")

    assert "manualChunks" in source
    assert "vendor-react" in source
    assert "vendor-markdown" in source
    assert "vendor-terminal" in source
    assert "vendor-state" in source


def test_terminal_modal_is_lazy_loaded_from_session_sidebar():
    source = Path("frontend/src/features/sessions/SessionSidebar.tsx").read_text(
        encoding="utf-8"
    )

    assert "lazy(() => import('./SessionTerminalModal'))" in source
    assert "import SessionTerminalModal from './SessionTerminalModal'" not in source
    assert "<Suspense fallback={<TerminalModalFallback />}" in source

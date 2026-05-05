from core.session_profile import _fallback_profile, profile_to_markdown, profile_to_system_prompt


def test_fallback_profile_marks_database_focus_area():
    context = {
        "session_id": "sid-1",
        "asset_key": "oracle:oracle:10.0.0.1:1521",
        "host": "10.0.0.1",
        "port": 1521,
        "remark": "核心 Oracle",
        "asset_type": "oracle",
        "protocol": "oracle",
        "tags": ["数据库"],
    }
    inspection = {
        "summary": "数据库只读巡检完成。",
        "checks": [
            {"title": "数据库只读 SQL 探测", "status": "success", "output": '{"success": true}'}
        ],
    }

    profile = _fallback_profile("sid-1", context, inspection, "fallback")

    assert profile["role_category"] == "database"
    assert "数据库" in profile["role_label"]
    assert profile["risk_level"] == "normal"
    assert profile["focus_areas"][0]["priority"] == "P0"
    assert "数据库" in profile_to_markdown(profile)


def test_fallback_profile_raises_risk_for_multiple_failed_checks():
    context = {
        "session_id": "sid-2",
        "asset_key": "linux:ssh:10.0.0.2:22",
        "host": "10.0.0.2",
        "port": 22,
        "asset_type": "linux",
        "protocol": "ssh",
    }
    inspection = {
        "checks": [
            {"title": "内存", "status": "error", "output": "free failed"},
            {"title": "磁盘", "status": "error", "output": "df failed"},
            {"title": "服务", "status": "warning", "output": "failed units"},
        ],
    }

    profile = _fallback_profile("sid-2", context, inspection, "fallback")

    assert profile["role_category"] == "linux"
    assert profile["risk_level"] == "high"
    assert profile["confidence"] > 0


def test_profile_prompt_is_reused_without_manual_realtime_confirmation_wording():
    prompt = profile_to_system_prompt(
        {
            "profile_prompt": "这是核心 Linux 应用服务器，优先关注 Docker、SSH 和系统日志。",
        }
    )

    assert "不需要每轮人工确认" in prompt
    assert "实时工具结果验证" not in prompt


def test_profile_to_system_prompt_synthesizes_from_structured_profile_when_prompt_missing():
    prompt = profile_to_system_prompt(
        {
            "role_label": "ISO27001 合规审计系统后端服务器",
            "purpose": "承载 ISO27001 合规审计平台的前后端容器服务。",
            "risk_level": "normal",
            "confidence": 92,
            "focus_areas": [
                {
                    "priority": "P1",
                    "title": "SSH 访问控制",
                    "reason": "确认登录审计和密钥轮换策略。",
                }
            ],
        }
    )

    assert "ISO27001 合规审计系统后端服务器" in prompt
    assert "SSH 访问控制" in prompt
    assert "不需要每轮人工确认" in prompt

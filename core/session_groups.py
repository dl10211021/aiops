"""Session group helpers.

The current runtime session model stores the primary session group in
``tags[0]``. Keeping that compatibility rule here prevents API handlers and
frontend-facing services from reimplementing it differently.
"""

DEFAULT_SESSION_GROUP = "未分组"
MAX_SESSION_GROUP_NAME_LENGTH = 80


def normalize_session_group_name(value: str | None) -> str:
    name = " ".join(str(value or "").strip().split())
    return name[:MAX_SESSION_GROUP_NAME_LENGTH]


def apply_primary_session_group(tags: list[str] | None, group_name: str) -> list[str]:
    normalized_group = normalize_session_group_name(group_name)
    if not normalized_group:
        raise ValueError("会话组名称不能为空")

    tail_tags = [
        tag
        for tag in (normalize_session_group_name(item) for item in (tags or [])[1:])
        if tag and tag != normalized_group
    ]
    return [normalized_group, *tail_tags]

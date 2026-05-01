import re

import yaml

from core.custom_skill_storage import CustomSkillStorageError, normalize_custom_skill_file_name


EXECUTABLE_SKILL_SUFFIXES = (".py", ".sh", ".ps1", ".bat", ".cmd")


def validate_skill_frontmatter(skill_id: str, content: str) -> tuple[bool, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.DOTALL)
    if not match:
        return False, "SKILL.md 必须以 YAML frontmatter 开头"
    try:
        frontmatter = yaml.safe_load(match.group(1).strip()) or {}
    except Exception as e:
        return False, f"SKILL.md frontmatter 解析失败: {e}"
    name = str(frontmatter.get("name") or "").strip()
    description = str(frontmatter.get("description") or "").strip()
    if not name or not description:
        return False, "SKILL.md frontmatter 必须包含 name 和 description"
    if name != skill_id:
        return False, "SKILL.md frontmatter name 必须与 skill_id 一致"
    return True, ""


def validate_skill_candidate(
    skill_id: str,
    file_name: str,
    content: str,
    *,
    allow_nested: bool = False,
) -> dict:
    normalized_skill_id = str(skill_id or "").strip()
    safe_file = str(file_name or "").strip()
    text = str(content or "")
    issues = []
    warnings = []

    if not re.fullmatch(r"[A-Za-z0-9_-]+", normalized_skill_id):
        issues.append(
            {
                "code": "invalid_skill_id",
                "message": "非法 skill_id：只能包含英文字母、数字、下划线和横线。",
            }
        )

    try:
        safe_file = normalize_custom_skill_file_name(safe_file, allow_nested=allow_nested)
    except CustomSkillStorageError as exc:
        issues.append({"code": "invalid_file_name", "message": exc.detail})

    if safe_file == "SKILL.md":
        valid, reason = validate_skill_frontmatter(normalized_skill_id, text)
        if not valid:
            issues.append({"code": "invalid_frontmatter", "message": reason})
    elif safe_file.lower().endswith(EXECUTABLE_SKILL_SUFFIXES):
        warnings.append(
            {
                "code": "executable_file",
                "message": "该文件可能包含可执行脚本，保存和运行应走审批与审计。",
            }
        )

    if not text.strip():
        issues.append({"code": "empty_content", "message": "技能文件内容不能为空。"})

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "skill_id": normalized_skill_id,
        "file_name": safe_file,
    }

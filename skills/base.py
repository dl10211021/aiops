from typing import Dict, Any, List

class BaseSkillProvider:
    """所有技能组的基础接口"""
    def get_tools(self) -> List[Dict[str, Any]]:
        """返回符合 OpenAI 格式的工具定义列表"""
        return []
    
    def execute(self, tool_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> str:
        """执行具体的技能工具"""
        raise NotImplementedError

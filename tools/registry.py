from typing import Callable
from inspect import signature

class ToolRegistry:
    """管理和执行 Agent 可使用的工具。"""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
    ) -> None:
        if name in self._tools:
            raise ValueError(f"工具已存在: {name}")
        
        self._tools[name] = func
        self._descriptions[name] = description

    def has_tool(self, name: str) -> bool:
        return name in self._tools
    
    def execute(self, name: str, **kwargs) -> str:
        """校验参数后执行工具。"""
        if not self.has_tool(name):
            return f"错误:未定义的工具 '{name}'"

        func = self._tools[name]
        tool_signature = signature(func)

        try:
            bound_arguments = tool_signature.bind(**kwargs)
        except TypeError as exc:
            return f"错误:工具 '{name}' 参数错误: {exc}"

        try:
            return func(**bound_arguments.arguments)
        except Exception as exc:
            return f"错误:工具 '{name}' 执行失败: {exc}"
    
    def describe(self) -> str:
        if not self._tools:
            return "暂无可用工具"

        lines = []
        for name, func in self._tools.items():
            parameters = signature(func)
            description = self._descriptions[name]
            lines.append(f"- {name}{parameters}: {description}")

        return "\n".join(lines)

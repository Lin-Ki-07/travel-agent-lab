from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any, Callable

@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None

class ToolRegistry:
    """管理和执行 Agent 可使用的工具。"""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._descriptions: dict[str, str] = {}
        self._parameters: dict[str, list[ToolParameter]] = {}
    
    def _infer_parameters(
        self,
        func: Callable,
    ) -> list[ToolParameter]:
        """从函数签名推断基础参数信息。"""

        result = []

        for parameter in signature(func).parameters.values():
            if parameter.kind in (
                Parameter.VAR_POSITIONAL,
                Parameter.VAR_KEYWORD,
            ):
                continue

            annotation = parameter.annotation

            if annotation is str:
                type_name = "string"
            elif annotation is int:
                type_name = "integer"
            elif annotation is float:
                type_name = "number"
            elif annotation is bool:
                type_name = "boolean"
            else:
                type_name = "string"

            required = parameter.default is Parameter.empty
            default = (
                None
                if required
                else parameter.default
            )

            result.append(
                ToolParameter(
                    name=parameter.name,
                    type=type_name,
                    description=f"{parameter.name} 参数",
                    required=required,
                    default=default,
                )
            )

        return result

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: list[ToolParameter] | None = None,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"工具已存在: {name}")
        
        self._tools[name] = func
        self._descriptions[name] = description
        self._parameters[name] = parameters or self._infer_parameters(func)

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
            parameters = self._parameters[name]
            description = self._descriptions[name]

            parameter_text = ", ".join(
                f"{parameter.name}: {parameter.type}"
                for parameter in parameters
            )

            lines.append(
                f"- {name}({parameter_text}): {description}"
            )

        return "\n".join(lines)

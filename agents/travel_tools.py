from tools.attraction_tool import search_travel_evidence
from tools.registry import ToolParameter, ToolRegistry
from tools.weather_tool import WeatherTool


def create_travel_tool_registry() -> ToolRegistry:
    """创建只读旅行工具集合；不包含记忆或行程写入工具。"""
    registry = ToolRegistry()
    registry.register_tool(WeatherTool())
    registry.register_function(
        name="search_travel_evidence",
        func=search_travel_evidence,
        description="按旅行问题搜索网页资料，返回编号、标题、URL 和文本证据",
        parameters=[
            ToolParameter(
                name="question",
                type="string",
                description="需要检索的完整旅行问题",
            ),
        ],
    )
    return registry
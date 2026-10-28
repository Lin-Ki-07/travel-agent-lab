import ast
import re
from typing import Any

from core.llm_client import OpenAICompatibleClient
from core.message import Message
from core.exceptions import LLMError
from core.config import AgentConfig
from tools.registry import ToolRegistry
from agents.base import Agent


class ReActAgent(Agent):
    def __init__(
            self,
            name: str,
            llm: OpenAICompatibleClient,
            tool_registry: ToolRegistry,
            system_prompt: str,
            config: AgentConfig | None = None,
    ):
        
        self.config = config if config is not None else AgentConfig()

        super().__init__(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            max_history_messages=self.config.max_history_messages,
        )

        self.tool_registry = tool_registry
        
    def _parse_action(self, llm_output: str) -> str | None:
        """从模型输出中提取 Action 内容。"""
        action_match = re.search(
            r"Action:\s*(.*)",
            llm_output,
            re.DOTALL,
        )

        if not action_match:
            return None
        return action_match.group(1).strip()

    def _parse_tool_call(
            self,
            action_str:str,
    ) -> tuple[str, dict[str, Any]] | None:
        """解析工具调用，只允许关键字参数。"""

        try:
            expression = ast.parse(
                action_str,
                mode="eval",
            ).body
        except SyntaxError:
            return None
        
        if not isinstance(expression, ast.Call):
            return None
        
        if not isinstance(expression.func, ast.Name):
            return None
        
        if expression.args:
            # 当前协议只支持 key=value，不支持位置参数
            return None
        
        kwargs: dict[str, Any] = {}

        for keyword in expression.keywords:
            if keyword.arg is None:
                # 拒绝 **data 这种展开参数
                return None
            try:
                kwargs[keyword.arg] = ast.literal_eval(keyword.value)
            except (ValueError, TypeError, SyntaxError):
                # 只接受字符串、数字、布尔值、列表等字面量
                return None
        return expression.func.id, kwargs

    def run(self, user_prompt: str) -> str:
        """执行一轮任务，仅保留成功轮次的历史。"""
        previous_history = self.get_history()

        try:
            answer = self._run(user_prompt)
        except LLMError:
            self._history = previous_history
            raise

        if answer is None:
            self._history = previous_history
            return f"未能在 {self.config.max_steps} 步内完成任务。"

        return answer

    def _run(self, user_prompt: str) -> str | None:
        self.add_message(
            Message(
                role="user",
                content=user_prompt,
            )
        )

        system_prompt = self.system_prompt.format(
            tools=self.tool_registry.describe(),
        )

        print(f"用户输入: {user_prompt}\n" + "="*40)

        # --- 运行主循环 ---
        for i in range(self.config.max_steps): 
            print(f"--- 循环 {i+1} ---\n")
            
            #  调用LLM进行思考
            llm_output = self.llm.generate(
                self.get_history(),
                system_prompt=system_prompt,
            )

            # 模型可能会输出多余的Thought-Action，需要截断
            match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
            if match:
                truncated = match.group(1).strip()
                if truncated != llm_output.strip():
                    llm_output = truncated
                    print("已截断多余的 Thought-Action 对")
            print(f"模型输出:\n{llm_output}\n")
            self.add_message(
                Message(
                    role="assistant",
                    content=llm_output,
                )
            )
            
            # 解析 Action
            action_str = self._parse_action(llm_output)

            if action_str is None:
                observation = (
                    "错误: 未能解析到 Action 字段。"
                    "请确保回复包含 Action: ..."
                )
                observation_str = f"Observation: {observation}"
                print(f"{observation_str}\n" + "=" * 40)
                self.add_message(
                    Message(
                        role="tool",
                        content=observation,
                    )
                )
                continue
            
            # 处理最终结果
            if action_str.startswith("Finish"):
                finish_match = re.fullmatch(
                    r"Finish\[(.*)\]",
                    action_str,
                    re.DOTALL,
                )

                if finish_match:
                    return finish_match.group(1).strip()
                
                observation = (
                    "错误: Finish 格式不正确。"
                    "正确格式应为 Finish[最终答案]"
                )
                observation_str = f"Observation: {observation}"
                print(f"{observation_str}\n" + "=" * 40)
                self.add_message(
                    Message(
                        role="tool",
                        content=observation,
                    )
                )
                continue

            # 处理工具调用
            tool_call = self._parse_tool_call(action_str)

            if tool_call is None:
                observation = (
                    "错误: 工具调用格式不正确。"
                    "正确格式应为 tool_name(arg=\"value\")"
                )
                observation_str = f"Observation: {observation}"
                print(f"{observation_str}\n" + "=" * 40)
                self.add_message(
                    Message(
                        role="tool",
                        content=observation,
                    )
                )
                continue
            
            tool_name, kwargs = tool_call
            observation = self.tool_registry.execute(tool_name, **kwargs)
            self.add_message(
                Message(
                    role="tool",
                    content=observation,
                )
            )
            # 记录观察结果
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)

        # 达到循环上限，通知 run() 恢复历史。
        return None

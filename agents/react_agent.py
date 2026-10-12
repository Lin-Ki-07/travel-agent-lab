import re
from core.llm_client import OpenAICompatibleClient
from tools.registry import ToolRegistry

class ReActAgent:
    def __init__(
            self,
            llm: OpenAICompatibleClient,
            tool_registry: ToolRegistry,
            system_prompt: str,
            max_steps: int = 5,
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.max_steps = max_steps
    
    def run(self,user_prompt: str) -> str:
        prompt_history = [f"用户请求: {user_prompt}"]

        print(f"用户输入: {user_prompt}\n" + "="*40)

        # --- 运行主循环 ---
        for i in range(self.max_steps): 
            print(f"--- 循环 {i+1} ---\n")
            
            #  构建Prompt
            full_prompt = "\n".join(prompt_history)
            
            #  调用LLM进行思考
            llm_output = self.llm.generate(
                full_prompt, 
                system_prompt=self.system_prompt
            )
            # 模型可能会输出多余的Thought-Action，需要截断
            match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
            if match:
                truncated = match.group(1).strip()
                if truncated != llm_output.strip():
                    llm_output = truncated
                    print("已截断多余的 Thought-Action 对")
            print(f"模型输出:\n{llm_output}\n")
            prompt_history.append(llm_output)
            
            # 解析并执行行动
            action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
            if not action_match:
                observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
                observation_str = f"Observation: {observation}"
                print(f"{observation_str}\n" + "="*40)
                prompt_history.append(observation_str)
                continue
            action_str = action_match.group(1).strip()

            if action_str.startswith("Finish"):
                final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
                return final_answer
            
            tool_name = re.search(r"(\w+)\(", action_str).group(1)
            args_str = re.search(r"\((.*)\)", action_str).group(1)
            kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

            # 记录观察结果
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)

        # 达到循环上限
        return f"未能在 {self.max_steps} 步内完成任务。"

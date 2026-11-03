import os
from tavily import TavilyClient

def get_attraction(city: str, weather: str) -> str:
    """
    搜索旅行资料，返回带来源编号的证据。
    """
    # 从环境变量中读取API密钥
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误:未配置TAVILY_API_KEY环境变量。"
    
    # 构造一个精确的查询
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"
    
    try:
        response = TavilyClient(api_key=api_key).search(
            query=query,
            search_depth="basic",
            include_answer=False,
            timeout=10,
        )
    except Exception as exc:
        return f"搜索失败：Tavily 请求未完成（{type(exc).__name__}）。"

    evidence = []
    for result in response.get("results", []):
        title = str(result.get("title") or "").strip()
        url = str(result.get("url") or "").strip()
        content = str(result.get("content") or "").strip()

        if not (title and url and content):
            continue

        number = len(evidence) + 1
        evidence.append(
            f"[{number}] 标题：{title}\n"
            f"URL：{url}\n"
            f"文本：{content[:500]}"
        )
        
        if len(evidence) == 5:
            break
        
    if not evidence:
        return "搜索完成，但没有找到可引用的旅行资料。"
    
    return "本次搜索证据：\n" + "\n\n".join(evidence)
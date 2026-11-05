from core.trip_input import parse_trip_request
from core.trip_models import TripRequest


def collect_trip_request(input_fn=input) -> TripRequest:
    """从命令行收集字段，并在调用外部服务前完成校验。"""
    print("请填写旅行需求；同行人数、预算和偏好可留空。")
    raw = {
        "destination": input_fn("目的地："),
        "start_date": input_fn("出发日期（YYYY-MM-DD）："),
        "days": input_fn("旅行天数（与结束日期二选一）："),
        "end_date": input_fn("结束日期（与天数二选一）："),
        "travelers": input_fn("同行人数（默认 1）："),
        "budget_cny": input_fn("全体同行者的全程预算，人民币（可留空）："),
        "preferences": input_fn("偏好，用英文逗号分隔（可留空）："),
    }
    return parse_trip_request(raw)
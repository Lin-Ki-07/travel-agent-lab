from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TripRequest:
    destination: str
    start_date: date
    days: int
    travelers: int = 1
    budget_cny: int | None = None
    preferences: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.destination.strip():
            raise ValueError("目的地不能为空")
        if self.days < 1:
            raise ValueError("旅行天数必须大于等于 1")
        if self.travelers < 1:
            raise ValueError("同行人数必须大于等于 1")
        if self.budget_cny is not None and self.budget_cny < 0:
            raise ValueError("预算不能为负数")
        if any(not preference.strip() for preference in self.preferences):
            raise ValueError("偏好不能包含空字符串")
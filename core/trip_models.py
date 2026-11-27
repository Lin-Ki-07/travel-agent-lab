from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from math import isfinite


@dataclass(frozen=True)
class RoutePart:
    mode: str
    positions: list[list[float]]

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str) or not self.mode.strip():
            raise ValueError("路线分段方式不能为空")
        if not isinstance(self.positions, list) or len(self.positions) < 2:
            raise ValueError("路线分段至少需要两个坐标")
        for point in self.positions:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("路线坐标必须为经纬度数对")
            if any(type(v) not in (int, float) or not isfinite(v) for v in point):
                raise ValueError("路线坐标必须为有限数值")
            if not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
                raise ValueError("路线坐标超出范围")


@dataclass(frozen=True)
class RouteSnapshot:
    status: str
    source: str
    queried_at: datetime
    distance_meters: int | None = None
    duration_seconds: int | None = None
    parts: list[RoutePart] = field(default_factory=list)
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("ok", "failed"):
            raise ValueError("路线状态必须为 ok 或 failed")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("路线来源不能为空")
        if not isinstance(self.queried_at, datetime) or self.queried_at.utcoffset() is None:
            raise ValueError("路线查询时间必须包含时区")
        if not isinstance(self.parts, list) or any(not isinstance(p, RoutePart) for p in self.parts):
            raise ValueError("路线分段类型不合法")
        if self.status == "ok":
            if any(type(v) is not int or v <= 0 for v in (self.distance_meters, self.duration_seconds)):
                raise ValueError("成功路线的距离和耗时必须为正整数")
            if not self.parts or self.failure_reason is not None:
                raise ValueError("成功路线必须有几何且不能有失败原因")
        elif (self.distance_meters is not None or self.duration_seconds is not None or self.parts
              or not isinstance(self.failure_reason, str) or not self.failure_reason.strip()):
            raise ValueError("失败路线只能保留来源、时间和失败原因")


def parse_route_snapshot(data: dict | None) -> RouteSnapshot | None:
    """仅用于程序可信的持久化快照；不接受模型或编辑请求作为事实来源。"""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("路线快照必须是对象")
    try:
        return RouteSnapshot(
            status=data["status"], source=data["source"],
            queried_at=datetime.fromisoformat(data["queried_at"]),
            distance_meters=data.get("distance_meters"),
            duration_seconds=data.get("duration_seconds"),
            parts=[RoutePart(**part) for part in data.get("parts", [])],
            failure_reason=data.get("failure_reason"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("路线快照字段不合法") from exc


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
    
@dataclass(frozen=True)
class Place:
    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    source: str
    queried_at: datetime
    citycode: str | None = None

    def __post_init__(self) -> None:
        if not self.place_id.strip():
            raise ValueError("地点 ID 不能为空")
        if not self.name.strip():
            raise ValueError("地点名称不能为空")
        if self.citycode is not None and (
            not isinstance(self.citycode, str)
            or not self.citycode.isascii() or not self.citycode.isdecimal()
        ):
            raise ValueError("城市编码必须为非空 ASCII 数字字符串或 None")
        if not self.source.strip():
            raise ValueError("地点来源不能为空")
        if not -90 <= self.latitude <= 90:
            raise ValueError("纬度必须在 -90 到 90 之间")
        if not -180 <= self.longitude <= 180:
            raise ValueError("经度必须在 -180 到 180 之间")
        if self.queried_at.tzinfo is None:
            raise ValueError("查询时间必须包含时区")

@dataclass(frozen=True)
class WeatherSnapshot:
    forecast_date: date
    condition: str | None
    min_temp_c: float | None
    max_temp_c: float | None
    available: bool
    source: str
    queried_at: datetime

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("天气来源不能为空")
        if self.queried_at.tzinfo is None:
            raise ValueError("天气查询时间必须包含时区")

        if not self.available:
            if any(value is not None for value in (
                self.condition,
                self.min_temp_c,
                self.max_temp_c,
            )):
                raise ValueError("无预报时不能填写天气信息")
            return

        if not self.condition or not self.condition.strip():
            raise ValueError("有预报时必须填写天气描述")
        if self.min_temp_c is None or self.max_temp_c is None:
            raise ValueError("有预报时必须填写最低和最高温度")
        if self.min_temp_c > self.max_temp_c:
            raise ValueError("最低温度不能高于最高温度")
        
@dataclass(frozen=True)
class Activity:
    place_id: str
    description: str
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if not self.place_id.strip():
            raise ValueError("活动地点 ID 不能为空")
        if not self.description.strip():
            raise ValueError("活动内容不能为空")
        if self.start_time >= self.end_time:
            raise ValueError("活动开始时间必须早于结束时间")


@dataclass(frozen=True)
class TransportSegment:
    from_place_id: str
    to_place_id: str
    mode: str
    estimated_minutes: int | None = None
    route: RouteSnapshot | None = None

    def __post_init__(self) -> None:
        if self.route is not None:
            if not isinstance(self.route, RouteSnapshot):
                raise ValueError("路线快照类型不合法")
            expected = ((self.route.duration_seconds + 59) // 60
                        if self.route.status == "ok" else None)
            if self.estimated_minutes != expected:
                raise ValueError("预计分钟数必须与路线快照一致")
        if not self.from_place_id.strip() or not self.to_place_id.strip():
            raise ValueError("交通段起终点 ID 不能为空")
        if self.from_place_id == self.to_place_id:
            raise ValueError("交通段起点和终点不能相同")
        if not self.mode.strip():
            raise ValueError("交通方式不能为空")
        if self.estimated_minutes is not None and self.estimated_minutes <= 0:
            raise ValueError("预估交通时间必须大于 0")
        
@dataclass(frozen=True)
class DailyPlan:
    day_number: int
    plan_date: date
    weather: WeatherSnapshot
    activities: list[Activity]
    transport_segments: list[TransportSegment] = field(default_factory=list)
    estimated_cost_cny: int | None = None
    cost_basis: str | None = None

    def __post_init__(self) -> None:
        if self.day_number < 1:
            raise ValueError("行程日序号必须大于等于 1")
        if self.weather.forecast_date != self.plan_date:
            raise ValueError("每日天气日期必须与行程日期一致")
        if not self.activities:
            raise ValueError("每日行程至少需要一项活动")
        if self.estimated_cost_cny is not None:
            if type(self.estimated_cost_cny) is not int or self.estimated_cost_cny < 0:
                raise ValueError("每日预计费用必须是非负整数")
            if not self.cost_basis or not self.cost_basis.strip():
                raise ValueError("填写每日预计费用时必须说明估算依据")
        elif self.cost_basis is not None:
            raise ValueError("每日费用未知时，估算依据必须为 null")

@dataclass(frozen=True)
class Itinerary:
    request: TripRequest
    places: list[Place]
    daily_plans: list[DailyPlan]
    estimated_total_cny: int | None
    generated_at: datetime
    web_evidence: str = ""

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("生成时间必须包含时区")
        if len(self.daily_plans) != self.request.days:
            raise ValueError("每日计划数量必须等于旅行天数")
        if self.estimated_total_cny is not None and self.estimated_total_cny < 0:
            raise ValueError("预计总费用不能为负数")

        for index, plan in enumerate(self.daily_plans, start=1):
            expected_date = self.request.start_date + timedelta(days=index - 1)
            if plan.day_number != index:
                raise ValueError("每日计划序号必须从 1 连续递增")
            if plan.plan_date != expected_date:
                raise ValueError("每日计划日期必须从出发日期连续递增")

        daily_costs = [plan.estimated_cost_cny for plan in self.daily_plans]
        if any(cost is None for cost in daily_costs):
            if self.estimated_total_cny is not None:
                raise ValueError("每日费用未全部确定时，总费用必须为 null")
        else:
            if type(self.estimated_total_cny) is not int:
                raise ValueError("每日费用完整时，必须填写整数总费用")
            if self.estimated_total_cny != sum(daily_costs):
                raise ValueError("预计总费用必须等于每日费用之和")

        if (
            self.request.budget_cny is not None
            and self.estimated_total_cny is not None
            and self.estimated_total_cny > self.request.budget_cny
        ):
            raise ValueError("预计总费用超过用户预算")

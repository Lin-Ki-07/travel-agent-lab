import unittest
from dataclasses import replace
from datetime import date, datetime, time, timezone

from core.itinerary_validator import validate_itinerary
from core.trip_models import (
    Activity, DailyPlan, Itinerary, Place, TransportSegment,
    TripRequest, WeatherSnapshot,
)


class ValidateItineraryTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        trip_date = date(2026, 11, 20)
        request = TripRequest("杭州", trip_date, 1)
        places = [
            Place("P1", "地点一", "地址一", 30, 120, "test", now),
            Place("P2", "地点二", "地址二", 30.1, 120.1, "test", now),
        ]
        weather = WeatherSnapshot(trip_date, None, None, None, False, "test", now)
        day = DailyPlan(
            1, trip_date, weather,
            [
                Activity("P1", "上午", time(9), time(10)),
                Activity("P2", "下午", time(11), time(12)),
            ],
            [TransportSegment("P1", "P2", "步行")],
        )
        self.trip = Itinerary(request, places, [day], None, now)

    def test_valid_trip(self):
        self.assertIs(validate_itinerary(self.trip), self.trip)

    def test_unknown_activity_place(self):
        day = replace(
            self.trip.daily_plans[0],
            activities=[Activity("missing", "参观", time(9), time(10))],
            transport_segments=[],
        )
        with self.assertRaisesRegex(ValueError, "未查询到的地点"):
            validate_itinerary(replace(self.trip, daily_plans=[day]))

    def test_overlapping_activities(self):
        day = replace(
            self.trip.daily_plans[0],
            activities=[
                Activity("P1", "上午", time(9), time(11)),
                Activity("P2", "重叠", time(10), time(12)),
            ],
        )
        with self.assertRaisesRegex(ValueError, "时间重叠"):
            validate_itinerary(replace(self.trip, daily_plans=[day]))

    def test_transport_order_mismatch(self):
        day = replace(self.trip.daily_plans[0], transport_segments=[])
        with self.assertRaisesRegex(ValueError, "地点顺序"):
            validate_itinerary(replace(self.trip, daily_plans=[day]))


if __name__ == "__main__":
    unittest.main()
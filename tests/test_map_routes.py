import unittest
from dataclasses import replace
from datetime import timedelta

from core.map_view import build_map_days
from core.trip_models import RoutePart, RouteSnapshot, TransportSegment
import test_trip_persistence_edit as fixtures


class MapRoutesTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.TripPersistenceEditTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.trip = fixture.trip
        self.day = self.trip.daily_plans[0]

    def map_day(self, day):
        return build_map_days(replace(self.trip, daily_plans=[day]))[0]

    def test_success_preserves_parts_and_does_not_mutate_snapshot(self):
        parts = [RoutePart('walking', [[120, 30], [120.05, 30.05]]),
                 RoutePart('transit', [[120.06, 30.06], [120.1, 30.1]])]
        route = RouteSnapshot('ok', 'amap', self.trip.generated_at, 100, 61, parts)
        day = replace(self.day, transport_segments=[TransportSegment('P1', 'P2', '公交', 2, route)])
        result = self.map_day(day)
        self.assertEqual(result['stops'], self.map_day(self.day)['stops'])
        segment = result['segments'][0]
        self.assertEqual(segment['kind'], 'route_snapshot')
        self.assertEqual([p['mode'] for p in segment['parts']], ['walking', 'transit'])
        self.assertEqual(segment['parts'][1]['positions'], parts[1].positions)
        segment['parts'][0]['positions'][0][0] = 0
        self.assertEqual(parts[0].positions[0][0], 120)

    def test_failed_and_missing_snapshots_use_endpoint_fallback(self):
        for route in [None, RouteSnapshot('failed', 'amap', self.trip.generated_at, failure_reason='未查询')]:
            day = replace(self.day, transport_segments=[TransportSegment('P1', 'P2', '步行', None, route)])
            segment = self.map_day(day)['segments'][0]
            self.assertEqual(segment['kind'], 'place_order_schematic')
            self.assertEqual(segment['parts'], [])
            self.assertEqual(segment['fallback_positions'], [[120, 30], [120.1, 30.1]])

    def test_repeated_stops_single_stop_and_multiple_days(self):
        repeated = replace(self.day, activities=[self.day.activities[0], *self.day.activities])
        result = self.map_day(repeated)
        self.assertEqual(len(result['stops']), 3)
        self.assertEqual(len(result['segments']), 1)
        self.assertEqual(result['segments'][0]['from_order'], 2)
        single = replace(self.day, activities=self.day.activities[:1], transport_segments=[])
        self.assertEqual(self.map_day(single)['segments'], [])
        next_date = self.day.plan_date + timedelta(days=1)
        second = replace(single, day_number=2, plan_date=next_date,
                         weather=replace(single.weather, forecast_date=next_date))
        days = build_map_days(replace(self.trip, request=replace(self.trip.request, days=2),
                                      daily_plans=[self.day, second]))
        self.assertEqual([len(d['segments']) for d in days], [1, 0])

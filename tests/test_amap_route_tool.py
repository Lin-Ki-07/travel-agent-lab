import unittest
from datetime import date, datetime, time, timezone
from unittest.mock import patch

import requests

from core.trip_models import Place
from tools.amap_route_tool import query_amap_route


class AmapRouteTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.a = Place("a", "甲", "", 30.123456789, 120, "amap", now)
        self.b = Place("b", "乙", "", 30.2, 120.2, "amap", now)
        self.polyline = "120,30;120.2,30.2"

    def query(self, mode="walking", **kwargs):
        return query_amap_route(self.a, self.b, mode, api_key="test-key", **kwargs)

    def test_walking_and_driving_contract(self):
        plan = {"distance": "120", "cost": {"duration": "61"},
                "steps": [{"polyline": self.polyline}]}
        for mode in ("walking", "driving"):
            with self.subTest(mode=mode), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "route": {"paths": [plan]}}
                route = self.query(mode)
                self.assertEqual((route.status, route.distance_meters, route.duration_seconds), ("ok", 120, 61))
                self.assertEqual(route.parts[0].positions, [[120, 30], [120.2, 30.2]])
                self.assertEqual(route.parts[0].mode, mode)
                self.assertIsNotNone(route.queried_at.utcoffset())
                self.assertTrue(get.call_args.args[0].endswith('/' + mode))
                self.assertEqual(get.call_args.kwargs["params"]["origin"], "120.000000,30.123457")
                self.assertEqual(get.call_args.kwargs["params"]["show_fields"], "cost,polyline")
                self.assertEqual(get.call_args.kwargs["timeout"], (5, 10))

    def test_transit_preserves_walking_and_bus_parts(self):
        plan = {"distance": "1200", "cost": {"duration": "600"}, "segments": [{
            "walking": {"steps": [{"polyline": self.polyline}]},
            "bus": {"buslines": [{"polyline": self.polyline}, {"polyline": "bad-alternative"}]},
        }]}
        with patch("tools.amap_route_tool.requests.get") as get:
            get.return_value.json.return_value = {"status": "1", "route": {"transits": [plan]}}
            route = self.query("transit", origin_citycode="010", destination_citycode="010",
                               departure_date=date(2026, 11, 26), departure_time=time(9, 5))
            self.assertEqual([p.mode for p in route.parts], ["walking", "transit"])
            params = get.call_args.kwargs["params"]
            self.assertEqual((params["city1"], params["date"], params["time"]), ("010", "2026-11-26", "09-05"))

    def test_invalid_inputs_do_not_request(self):
        with patch("tools.amap_route_tool.requests.get") as get:
            for mode, options in (("flight", {}), ("transit", {})):
                self.assertEqual(self.query(mode, **options).status, "failed")
            self.assertEqual(query_amap_route(self.a, self.b, "walking", api_key="").status, "failed")
            get.assert_not_called()

    def test_external_failures_are_safe_and_have_no_route_facts(self):
        cases = [requests.Timeout("test-key"), requests.HTTPError("test-key"),
                 ValueError("test-key"), {"status": "0", "infocode": "10009", "info": "test-key"},
                 {"status": "0", "infocode": "test-key"},
                 {"status": "1", "route": {"paths": []}}, [],
                 {"status": "1", "route": {"paths": [{"distance": "10", "cost": {"duration": "5"},
                                                           "steps": [{"polyline": "120,30;999,30"}]}]}},
                 {"status": "1", "route": {"paths": [None]}}]
        for case in cases:
            with self.subTest(case=case), patch("tools.amap_route_tool.requests.get") as get:
                if isinstance(case, requests.RequestException):
                    get.side_effect = case
                elif isinstance(case, Exception):
                    get.return_value.json.side_effect = case
                else:
                    get.return_value.json.return_value = case
                route = self.query()
                self.assertEqual(route.status, "failed")
                self.assertIsNone(route.distance_meters)
                self.assertIsNone(route.duration_seconds)
                self.assertEqual(route.parts, [])
                self.assertNotIn("test-key", route.failure_reason)

    def test_incomplete_transit_is_rejected(self):
        for segment in ({"railway": {"id": "train"}}, {"taxi": {"distance": "10"}}, {},
                        {"bus": {"buslines": [{"polyline": "bad"}]}}):
            with self.subTest(segment=segment), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "route": {"transits": [{
                    "distance": "10", "cost": {"duration": "5"}, "segments": [segment]}]}}
                self.assertEqual(self.query("transit", origin_citycode="010", destination_citycode="010").status, "failed")

    def test_transit_selects_first_complete_plan_without_additional_requests(self):
        valid = {"distance": "1200", "cost": {"duration": "600"}, "segments": [{
            "walking": {"steps": [{"polyline": self.polyline}]},
            "bus": {"buslines": [{"polyline": "120.2,30.2;120.3,30.3"}]},
        }]}
        invalid = [None, {}, {**valid, "distance": "0"}, {**valid, "cost": {}},
                   {**valid, "segments": []},
                   {**valid, "segments": [valid["segments"][0], {}]},
                   {**valid, "segments": [{"railway": {"id": "train"}}]},
                   {**valid, "segments": [{"taxi": {"distance": "10"}}]},
                   {**valid, "segments": [{"bus": {"buslines": [{"polyline": "bad"}]}}]}]
        later = {**valid, "distance": "2400", "cost": {"duration": "900"}}
        for bad in invalid:
            with self.subTest(bad=bad), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {
                    "status": "1", "route": {"transits": [bad, valid, later]}}
                route = self.query("transit", origin_citycode="010", destination_citycode="010")
                get.assert_called_once()
                self.assertEqual((route.status, route.distance_meters, route.duration_seconds),
                                 ("ok", 1200, 600))
                self.assertEqual([p.mode for p in route.parts], ["walking", "transit"])
                self.assertEqual(route.parts[1].positions, [[120.2, 30.2], [120.3, 30.3]])
        with patch("tools.amap_route_tool.requests.get") as get:
            get.return_value.json.return_value = {"status": "1", "route": {"transits": [valid, later]}}
            route = self.query("transit", origin_citycode="010", destination_citycode="010")
            get.assert_called_once()
            self.assertEqual(route.distance_meters, 1200)

    def test_all_transit_plans_invalid_returns_no_route_facts(self):
        for plans in ([], [None, {}, {"distance": "10", "cost": {"duration": "5"}, "segments": []}]):
            with self.subTest(plans=plans), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "route": {"transits": plans}}
                route = self.query("transit", origin_citycode="010", destination_citycode="010")
                get.assert_called_once()
                self.assertEqual(route.status, "failed")
                self.assertEqual(route.failure_kind, "no_route" if not plans else "unavailable")
                self.assertTrue(route.failure_reason)
                self.assertEqual(route.parts, [])
                self.assertIsNone(route.distance_meters)
                self.assertIsNone(route.duration_seconds)

    def test_subway_preference_thresholds_and_stable_ties(self):
        def plan(seconds, kind=None, name="地铁名称不能代替类型", distance="1200"):
            return {"distance": distance, "cost": {"duration": str(seconds)}, "segments": [{
                "bus": {"buslines": [{"polyline": self.polyline, "type": kind, "name": name}]}}]}
        cases = [
            ([plan(600), plan(750, "地铁线路")], 750),
            ([plan(600), plan(751, "地铁线路")], 600),
            ([plan(3600), plan(4500, "地铁线路")], 4500),
            ([plan(4000), plan(4901, "地铁线路")], 4000),
            ([plan(900), plan(600), plan(700)], 600),
            ([plan(600), plan(700, None)], 600),
            ([plan(600), plan(700, "普通公交")], 600),
            ([plan(600), plan(740, "地铁线路"), plan(700, "地铁线路")], 700),
            ([plan(600), {**plan(650, "地铁线路"), "segments": []}], 600),
        ]
        for plans, seconds in cases:
            with self.subTest(seconds=seconds, plans=plans), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "route": {"transits": plans}}
                route = self.query("transit", origin_citycode="010", destination_citycode="010")
                get.assert_called_once()
                self.assertEqual(get.call_args.kwargs["params"]["AlternativeRoute"], "5")
                self.assertEqual(route.duration_seconds, seconds)
        with patch("tools.amap_route_tool.requests.get") as get:
            get.return_value.json.return_value = {"status": "1", "route": {"transits": [
                plan(600, distance="1000"), plan(600, distance="2000")]}}
            self.assertEqual(self.query("transit", origin_citycode="010", destination_citycode="010").distance_meters, 1000)

    def test_service_failure_classification_and_legacy_snapshot(self):
        from dataclasses import asdict
        from core.trip_models import parse_route_snapshot
        for code, expected in (("10001", "blocked"), ("10003", "blocked"), ("10014", "blocked"),
                               ("20000", "blocked"), ("40000", "blocked"), ("20802", "no_route"),
                               ("unknown", "blocked")):
            with self.subTest(code=code), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "0", "infocode": code}
                route = self.query()
                self.assertEqual(route.failure_kind, expected)
                raw = asdict(route)
                raw["queried_at"] = route.queried_at.isoformat()
                self.assertEqual(parse_route_snapshot(raw), route)
                del raw["failure_kind"]
                self.assertIsNone(parse_route_snapshot(raw).failure_kind)


    def test_malformed_route_container_is_unavailable_not_no_route(self):
        for mode, field in (("walking", "paths"), ("transit", "transits")):
            for data in ({"status": "1"}, {"status": "1", "route": {}},
                         {"status": "1", "route": {field: None}},
                         {"status": "1", "route": {field: [None]}}):
                with self.subTest(mode=mode, data=data), patch("tools.amap_route_tool.requests.get") as get:
                    get.return_value.json.return_value = data
                    options = {"origin_citycode": "010", "destination_citycode": "010"} if mode == "transit" else {}
                    route = self.query(mode, **options)
                    self.assertEqual(route.failure_kind, "unavailable")
                    self.assertEqual(route.parts, [])
                    get.assert_called_once()


    def test_transit_nested_and_mixed_polylines_preserve_independent_parts(self):
        from itertools import product
        bus_points = "120.2,30.2;120.3,30.3"
        for nested_walk, nested_bus in product((False, True), repeat=2):
            with self.subTest(walking=nested_walk, bus=nested_bus), patch("tools.amap_route_tool.requests.get") as get:
                walk = {"polyline": self.polyline} if nested_walk else self.polyline
                bus = {"polyline": bus_points} if nested_bus else bus_points
                plan = {"distance": "1200", "cost": {"duration": "600"}, "segments": [
                    {"walking": {"steps": [{"polyline": walk}]},
                     "bus": {"buslines": [{"polyline": bus, "type": "地铁线路"},
                                          {"polyline": "bad-unused-alternative"}]}},
                    {"walking": {"steps": [{"polyline": walk}]}}]}
                get.return_value.json.return_value = {"status": "1", "route": {"transits": [plan]}}
                result = self.query("transit", origin_citycode="010", destination_citycode="010")
                self.assertEqual(result.status, "ok")
                self.assertEqual([p.mode for p in result.parts], ["walking", "transit", "walking"])
                self.assertEqual(result.parts[1].positions, [[120.2, 30.2], [120.3, 30.3]])
                self.assertEqual(result.parts[0].positions, result.parts[2].positions)
                get.assert_called_once()

    def test_bad_nested_transit_geometry_rejects_whole_candidate(self):
        from copy import deepcopy
        valid = {"distance": "1200", "cost": {"duration": "600"}, "segments": [{
            "walking": {"steps": [{"polyline": {"polyline": self.polyline}}]},
            "bus": {"buslines": [{"polyline": {"polyline": self.polyline}}]}}]}
        for bad in ({}, {"polyline": None}, {"polyline": []}, {"polyline": 12},
                    {"polyline": {"polyline": self.polyline}}, {"polyline": "bad"},
                    {"polyline": "120,30"}, {"polyline": "120,30;999,30"}):
            for field in ("walking", "bus"):
                broken = deepcopy(valid)
                segment = broken["segments"][0]
                target = segment["walking"]["steps"][0] if field == "walking" else segment["bus"]["buslines"][0]
                target["polyline"] = bad
                for plans, expected in (([broken], "failed"), ([broken, valid], "ok")):
                    with self.subTest(bad=bad, field=field, expected=expected), patch("tools.amap_route_tool.requests.get") as get:
                        get.return_value.json.return_value = {"status": "1", "route": {"transits": plans}}
                        result = self.query("transit", origin_citycode="010", destination_citycode="010")
                        self.assertEqual(result.status, expected)
                        self.assertEqual(len(result.parts), 2 if expected == "ok" else 0)
                        if expected == "failed":
                            self.assertEqual(result.failure_kind, "unavailable")
                        get.assert_called_once()

    def test_road_polyline_contract_remains_string_only(self):
        for mode in ("walking", "driving"):
            with self.subTest(mode=mode), patch("tools.amap_route_tool.requests.get") as get:
                get.return_value.json.return_value = {"status": "1", "route": {"paths": [{
                    "distance": "120", "cost": {"duration": "61"},
                    "steps": [{"polyline": {"polyline": self.polyline}}]}]}}
                result = self.query(mode)
                self.assertEqual(result.failure_kind, "unavailable")
                self.assertEqual(result.parts, [])

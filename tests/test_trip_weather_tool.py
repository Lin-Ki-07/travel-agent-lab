import unittest
from datetime import date
from unittest.mock import patch

import requests

from tools.trip_weather_tool import get_trip_weather


class TripWeatherTests(unittest.TestCase):
    def query(self):
        return get_trip_weather('青岛', date(2026, 11, 27), 1)

    def test_request_failures_are_classified_without_retry_or_raw_details(self):
        for error, message in [
            (requests.Timeout('private-url'), '天气服务请求超时'),
            (requests.ConnectionError('private-url'), '无法连接天气服务'),
            (requests.RequestException('private-url'), '天气服务请求失败'),
        ]:
            with self.subTest(message=message), patch('tools.trip_weather_tool.requests.get', side_effect=error) as get:
                with self.assertRaises(RuntimeError) as caught:
                    self.query()
                self.assertEqual(str(caught.exception), message)
                get.assert_called_once()
                self.assertEqual(get.call_args.kwargs['timeout'], (5, 10))

    def test_http_status_is_reported_without_body_or_url(self):
        response = requests.Response()
        response.status_code = 503
        with patch('tools.trip_weather_tool.requests.get', return_value=response) as get:
            with self.assertRaisesRegex(RuntimeError, '^天气服务返回 HTTP 503$'):
                self.query()
            get.assert_called_once()

    def test_invalid_json_and_response_shapes(self):
        for data, message in [(None, '天气响应格式不合法：应为对象'),
                              ([], '天气响应格式不合法：应为对象'),
                              ({}, '天气响应缺少逐日预报列表')]:
            with self.subTest(data=data), patch('tools.trip_weather_tool.requests.get') as get:
                get.return_value.json.return_value = data
                with self.assertRaises(RuntimeError) as caught:
                    self.query()
                self.assertEqual(str(caught.exception), message)
        with patch('tools.trip_weather_tool.requests.get') as get:
            get.return_value.json.side_effect = ValueError('private-body')
            with self.assertRaisesRegex(RuntimeError, '^天气响应不是有效 JSON$'):
                self.query()

    def test_valid_forecast_missing_date_and_malformed_fields(self):
        item = {'date': '2026-11-27', 'mintempC': '5', 'maxtempC': '12',
                'hourly': [{'time': '0', 'weatherDesc': [{'value': '晴'}]}]}
        with patch('tools.trip_weather_tool.requests.get') as get:
            get.return_value.json.return_value = {'weather': [item]}
            result = self.query()[0]
            self.assertTrue(result.available)
            self.assertEqual((result.min_temp_c, result.max_temp_c), (5, 12))
            get.return_value.json.return_value = {'weather': []}
            self.assertFalse(self.query()[0].available)
            get.return_value.json.return_value = {'weather': [{**item, 'hourly': [{'weatherDesc': [{'value': None}]}]}]}
            with self.assertRaisesRegex(RuntimeError, '天气预报字段不完整'):
                self.query()

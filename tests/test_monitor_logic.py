# -*- coding: utf-8 -*-
"""monitor_logic 纯逻辑单元测试（unittest，无第三方依赖）。"""

import os
import tempfile
import unittest

import settings as settings_mod
from monitor_logic import (
    REMINDER_END,
    REMINDER_END_ADVANCE,
    REMINDER_START,
    REMINDER_START_ADVANCE,
    decide_reminders,
    merge_sent_reminders,
    seconds_until_next_check,
)

NOW = 1_700_000_000


def make_contest(**kw):
    base = {
        'id': '1',
        'title': '测试赛',
        'status': '未开始',
        'startTime': NOW + 3600,
        'endTime': NOW + 7200,
    }
    base.update(kw)
    return base


class SecondsUntilNextCheckTest(unittest.TestCase):
    def test_empty_contests_returns_fallback(self):
        self.assertEqual(seconds_until_next_check([], NOW, 30, 30, 600), 600)

    def test_no_candidates_returns_fallback(self):
        contests = [make_contest(status='已结束', startTime=0, endTime=0)]
        self.assertEqual(seconds_until_next_check(contests, NOW, 30, 30, 600), 600)

    def test_sleeps_to_start_advance_point(self):
        st = NOW + 3600
        contests = [make_contest(startTime=st, endTime=st + 3600)]
        got = seconds_until_next_check(contests, NOW, 30, 0, 1_000_000)
        self.assertEqual(got, 3600 - 30 * 60)

    def test_sleeps_to_start_time_when_no_advance(self):
        st = NOW + 3600
        contests = [make_contest(startTime=st, endTime=st + 3600)]
        got = seconds_until_next_check(contests, NOW, 0, 0, 1_000_000)
        self.assertEqual(got, 3600)

    def test_ongoing_contest_sleeps_to_end_advance(self):
        et = NOW + 3600
        contests = [make_contest(status='进行中', startTime=NOW - 3600, endTime=et)]
        got = seconds_until_next_check(contests, NOW, 0, 30, 1_000_000)
        self.assertEqual(got, 3600 - 30 * 60)

    def test_ongoing_contest_sleeps_to_end_time_when_no_advance(self):
        et = NOW + 3600
        contests = [make_contest(status='进行中', startTime=NOW - 3600, endTime=et)]
        got = seconds_until_next_check(contests, NOW, 0, 0, 1_000_000)
        self.assertEqual(got, 3600)

    def test_picks_earliest_among_multiple(self):
        contests = [
            make_contest(id='1', startTime=NOW + 7200, endTime=NOW + 10800),
            make_contest(id='2', startTime=NOW + 300, endTime=NOW + 3600),
        ]
        got = seconds_until_next_check(contests, NOW, 0, 0, 1_000_000)
        self.assertEqual(got, 300)

    def test_far_future_trigger_is_capped_to_fallback(self):
        # 最近触发点在很久之后：不能一直睡到那一刻（会漏掉期间新增的比赛），
        # 应以回退轮询间隔先复查
        st = NOW + 7200
        contests = [make_contest(startTime=st, endTime=st + 3600)]
        got = seconds_until_next_check(contests, NOW, 30, 0, 600)
        self.assertEqual(got, 600)

    def test_recently_passed_trigger_triggers_quick_recheck(self):
        # 开始时间刚过不久（60 秒内），应尽快复查以捕捉状态切换
        contests = [make_contest(status='未开始', startTime=NOW - 30, endTime=NOW + 3600)]
        got = seconds_until_next_check(contests, NOW, 0, 0, 600)
        self.assertEqual(got, 1)

    def test_far_past_trigger_falls_back(self):
        contests = [make_contest(status='未开始', startTime=NOW - 7200, endTime=NOW + 3600)]
        got = seconds_until_next_check(contests, NOW, 0, 0, 600)
        self.assertEqual(got, 600)


class DecideRemindersTest(unittest.TestCase):
    def test_fires_start_advance_when_in_window(self):
        st = NOW + 15 * 60
        contest = make_contest(status='未开始', startTime=st, endTime=st + 3600)
        fired = decide_reminders(contest, '', [], NOW, advance_start_minutes=15)
        self.assertEqual(fired, [REMINDER_START_ADVANCE])

    def test_does_not_fire_start_advance_twice(self):
        st = NOW + 15 * 60
        contest = make_contest(status='未开始', startTime=st, endTime=st + 3600)
        fired = decide_reminders(contest, '', [REMINDER_START_ADVANCE], NOW,
                                 advance_start_minutes=15)
        self.assertEqual(fired, [])

    def test_no_start_advance_when_advance_zero(self):
        st = NOW + 15 * 60
        contest = make_contest(status='未开始', startTime=st, endTime=st + 3600)
        fired = decide_reminders(contest, '', [], NOW, advance_start_minutes=0)
        self.assertEqual(fired, [])

    def test_no_start_advance_outside_window(self):
        st = NOW + 60 * 60
        contest = make_contest(status='未开始', startTime=st, endTime=st + 3600)
        fired = decide_reminders(contest, '', [], NOW, advance_start_minutes=15)
        self.assertEqual(fired, [])

    def test_fires_start_on_transition(self):
        contest = make_contest(status='进行中', startTime=NOW - 60, endTime=NOW + 3600)
        fired = decide_reminders(contest, '未开始', [], NOW)
        self.assertEqual(fired, [REMINDER_START])

    def test_no_start_without_transition(self):
        contest = make_contest(status='进行中', startTime=NOW - 60, endTime=NOW + 3600)
        fired = decide_reminders(contest, '', [], NOW)
        self.assertEqual(fired, [])

    def test_fires_end_advance_when_ongoing(self):
        et = NOW + 10 * 60
        contest = make_contest(status='进行中', startTime=NOW - 3600, endTime=et)
        fired = decide_reminders(contest, '进行中', [], NOW, advance_end_minutes=10)
        self.assertEqual(fired, [REMINDER_END_ADVANCE])

    def test_no_end_advance_when_advance_zero(self):
        et = NOW + 10 * 60
        contest = make_contest(status='进行中', startTime=NOW - 3600, endTime=et)
        fired = decide_reminders(contest, '进行中', [], NOW, advance_end_minutes=0)
        self.assertEqual(fired, [])

    def test_fires_end_on_transition(self):
        contest = make_contest(status='已结束', startTime=NOW - 7200, endTime=NOW - 3600)
        fired = decide_reminders(contest, '进行中', [], NOW)
        self.assertEqual(fired, [REMINDER_END])

    def test_notify_on_start_false_suppresses_start_and_advance(self):
        st = NOW + 15 * 60
        contest = make_contest(status='未开始', startTime=st, endTime=st + 3600)
        fired = decide_reminders(contest, '未开始', [], NOW,
                                 advance_start_minutes=15, notify_on_start=False)
        self.assertEqual(fired, [])

    def test_notify_on_end_false_suppresses_end_and_advance(self):
        et = NOW + 10 * 60
        contest = make_contest(status='进行中', startTime=NOW - 3600, endTime=et)
        fired = decide_reminders(contest, '进行中', [], NOW,
                                 advance_end_minutes=10, notify_on_end=False)
        self.assertEqual(fired, [])


class MergeSentRemindersTest(unittest.TestCase):
    def test_inherits_sent_reminders_from_saved(self):
        current = {'1': make_contest(id='1')}
        saved = {'1': make_contest(id='1', sent_reminders=['start_advance'])}
        merge_sent_reminders(current, saved)
        self.assertEqual(current['1']['sent_reminders'], ['start_advance'])

    def test_defaults_to_empty_list_when_no_saved(self):
        current = {'1': make_contest(id='1')}
        merge_sent_reminders(current, {})
        self.assertEqual(current['1']['sent_reminders'], [])

    def test_does_not_touch_other_fields(self):
        current = {'1': make_contest(id='1', title='新标题')}
        saved = {'1': make_contest(id='1', sent_reminders=['start'])}
        merge_sent_reminders(current, saved)
        self.assertEqual(current['1']['title'], '新标题')
        self.assertEqual(current['1']['sent_reminders'], ['start'])


class SettingsDefaultsTest(unittest.TestCase):
    def test_default_settings_include_advance_keys(self):
        self.assertIn('advance_start_minutes', settings_mod.DEFAULT_SETTINGS)
        self.assertIn('advance_end_minutes', settings_mod.DEFAULT_SETTINGS)
        self.assertEqual(settings_mod.DEFAULT_SETTINGS['advance_start_minutes'], 0)
        self.assertEqual(settings_mod.DEFAULT_SETTINGS['advance_end_minutes'], 0)

    def test_advance_choices_valid(self):
        for v in settings_mod.ADVANCE_CHOICES:
            self.assertIsInstance(v, int)

    def test_settings_load_merges_advance_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            s = settings_mod.Settings(data_dir=d)
            self.assertEqual(s.get('advance_start_minutes'), 0)
            s.set('advance_start_minutes', 30)
            s2 = settings_mod.Settings(data_dir=d)
            self.assertEqual(s2.get('advance_start_minutes'), 30)


class MonitorIntegrationTest(unittest.TestCase):
    """端到端验证 ContestMonitor 的提前提醒触发与去重持久化（回归保护）。"""

    def _make_monitor(self, data_dir):
        import json as _json
        import time as _time
        import types
        import main as main_mod

        settings = settings_mod.Settings(data_dir=data_dir)
        # 关闭所有通知通道，避免测试时弹出真实窗口
        settings.set_multi({
            'popup_enabled': False,
            'message_enabled': False,
            'advance_start_minutes': 15,
        })
        monitor = main_mod.ContestMonitor(settings=settings)
        monitor.storage.data_file = os.path.join(data_dir, 'contests.json')

        st = int(_time.time()) + 10 * 60  # 10 分钟后开始
        fake_contests = [{
            'id': '100',
            'title': '即将开始的比赛',
            'status': '未开始',
            'time': '',
            'link': '',
            'startTime': st,
            'endTime': st + 3600,
        }]
        monitor.crawler = types.SimpleNamespace(fetch_contests=lambda: fake_contests)
        return monitor, fake_contests, _json, os.path.join(data_dir, 'contests.json')

    def test_advance_reminder_persisted_and_not_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            monitor, _, _json, data_file = self._make_monitor(d)

            monitor.check_contests()
            saved = _json.load(open(data_file, encoding='utf-8'))
            self.assertIn('start_advance', saved['contests']['100']['sent_reminders'])

            # 第二次检查不应重复触发提前提醒
            monitor.check_contests()
            saved2 = _json.load(open(data_file, encoding='utf-8'))
            self.assertEqual(
                saved2['contests']['100']['sent_reminders'],
                ['start_advance'],
            )


if __name__ == '__main__':
    unittest.main()

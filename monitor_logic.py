# -*- coding: utf-8 -*-
"""监控核心纯逻辑：触发点计算、提醒判定、去重状态合并与动态调度。

该模块不依赖 GUI / 网络 / 存储，便于单元测试。
"""

# 提醒类型常量（同时作为去重标识存储于比赛记录的 sent_reminders 中）
REMINDER_START_ADVANCE = 'start_advance'   # 比赛开始前提前提醒
REMINDER_START = 'start'                   # 比赛开始（未开始 -> 进行中）
REMINDER_END_ADVANCE = 'end_advance'       # 比赛结束前提前提醒
REMINDER_END = 'end'                       # 比赛结束（进行中 -> 已结束）

# 触发点刚刚过去后仍需要尽快复查的时间窗口（秒），用于捕捉状态切换
_RECHECK_GRACE = 60


def decide_reminders(contest, saved_status, sent, now_ts,
                     advance_start_minutes=0, advance_end_minutes=0,
                     notify_on_start=True, notify_on_end=True):
    """判定当前这一轮应该触发哪些提醒。

    参数：
        contest: 本次抓取到的比赛字典（含 status / startTime / endTime）
        saved_status: 上一轮保存的状态字符串（首次见到时为 ''）
        sent: 已发送过的提醒类型集合（去重）
        now_ts: 当前时间戳（秒）
        advance_start_minutes / advance_end_minutes: 提前量（分钟，0 表示不提前）
        notify_on_start / notify_on_end: 开始/结束提醒总开关

    返回：需要触发的提醒类型列表（按语义顺序）。
    """
    fired = []
    status = contest.get('status', '')
    st = contest.get('startTime', 0) or 0
    et = contest.get('endTime', 0) or 0
    sent = set(sent or [])

    # 开始前提前提醒：比赛尚未开始，且当前时间已进入提前窗口
    if notify_on_start and REMINDER_START_ADVANCE not in sent:
        if (status == '未开始' and advance_start_minutes > 0
                and st and now_ts >= st - advance_start_minutes * 60):
            fired.append(REMINDER_START_ADVANCE)

    # 比赛开始：状态从「未开始」切换为「进行中」
    if notify_on_start and REMINDER_START not in sent:
        if saved_status == '未开始' and status == '进行中':
            fired.append(REMINDER_START)

    # 结束前提前提醒：比赛进行中，且当前时间已进入结束提前窗口
    if notify_on_end and REMINDER_END_ADVANCE not in sent:
        if (status == '进行中' and advance_end_minutes > 0
                and et and now_ts >= et - advance_end_minutes * 60):
            fired.append(REMINDER_END_ADVANCE)

    # 比赛结束：状态从「进行中」切换为「已结束」
    if notify_on_end and REMINDER_END not in sent:
        if saved_status == '进行中' and status == '已结束':
            fired.append(REMINDER_END)

    return fired


def merge_sent_reminders(current_dict, saved_dict):
    """把上一轮快照中记录的已发送提醒合并到最新抓取结果上（跨重启去重）。

    参数：
        current_dict: 本次抓取到的 {id: contest} 字典（会被就地修改）
        saved_dict: 上一轮保存的 {id: contest} 字典
    返回：current_dict 本身。
    """
    for cid, contest in current_dict.items():
        saved = saved_dict.get(cid)
        sent = saved.get('sent_reminders', []) if saved else []
        contest['sent_reminders'] = list(sent)
    return current_dict


def seconds_until_next_check(contests, now_ts, advance_start_minutes,
                             advance_end_minutes, fallback_interval):
    """动态调度：计算距离下一个感兴趣触发点还有多少秒。

    触发点：
        - 「未开始」比赛：开始前提前提醒点（若有提前量）与开始时刻
        - 「进行中」比赛：结束前提前提醒点（若有提前量）与结束时刻

    规则：
        - 有未来触发点：睡到最早的那个（至少 1 秒）；但等待时间封顶为
          fallback_interval——触发点太远时先按轮询间隔复查，避免错过
          期间新上线的比赛
        - 最早触发点刚过不久（_RECHECK_GRACE 内）：1 秒后立即复查，
          以便捕捉「未开始 -> 进行中」等状态切换
        - 其余情况（无触发点 / 触发点早已过去）：回退到固定轮询间隔

    参数：
        contests: 当前已知比赛列表
        now_ts: 当前时间戳（秒）
        advance_start_minutes / advance_end_minutes: 提前量（分钟）
        fallback_interval: 无可用触发点时的轮询间隔（秒）
    返回：距离下次检查的秒数。
    """
    candidates = []
    for c in contests:
        st = c.get('startTime', 0) or 0
        et = c.get('endTime', 0) or 0
        status = c.get('status', '')
        if status == '未开始' and st:
            if advance_start_minutes > 0:
                candidates.append(st - advance_start_minutes * 60)
            candidates.append(st)
        elif status == '进行中' and et:
            if advance_end_minutes > 0:
                candidates.append(et - advance_end_minutes * 60)
            candidates.append(et)

    if not candidates:
        return fallback_interval

    earliest = min(candidates)
    if earliest > now_ts:
        return max(1, min(earliest - now_ts, fallback_interval))
    if earliest >= now_ts - _RECHECK_GRACE:
        return 1
    return fallback_interval

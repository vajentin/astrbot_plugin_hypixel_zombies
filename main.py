import aiohttp

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

MAP_ALIAS = {"de": "deadend", "bb": "badblood", "aa": "alienarcadium", "pr": "prison"}
MAP_CN = {
    "deadend": "穷途末路",
    "badblood": "坏血之宫",
    "alienarcadium": "外星游乐园",
    "prison": "监狱",
}

CLEAR_ROUND = {"deadend": 30, "badblood": 30, "prison": 30, "alienarcadium": 105}
DIFFS = ["normal", "hard", "rip"]

# 难度别名：英文/缩写/中文都认
DIFF_ALIAS = {
    "normal": "normal", "n": "normal", "普通": "normal",
    "hard": "hard", "h": "hard", "困难": "hard",
    "rip": "rip", "r": "rip", "安息": "rip",
}
DIFF_CN = {"normal": "普通", "hard": "困难", "rip": "安息"}

# ---------------------------------------------------------------------------
# 各图“特殊敌人/BOSS”击杀字段   规律：<敌人名>_zombie_kills_zombies
#   不确定的字段名跑 /zb <玩家> dump 核对。
# ---------------------------------------------------------------------------
MAP_BOSSES = {
    "alienarcadium": [
        ("巨人击杀", "giant_zombie_kills_zombies"),
        ("长者击杀", "the_old_one_zombie_kills_zombies"),
        ("彩虹巨人击杀", "giant_rainbow_zombie_kills_zombies"),
        ("世界毁灭者击杀", "world_ender_zombie_kills_zombies"),
    ],
    "deadend": [],
    "badblood": [],
    "prison": [],
}


def _g(d, key, default=0):
    return d.get(key, default)


def _n(x):
    try:
        return f"{int(x):,}"
    except (ValueError, TypeError):
        return str(x)


def fmt_time(seconds):
    """秒 -> H:MM:SS。
    ⚠️ 如果 dump 出来发现数值很大（像是毫秒），把下面 s = int(seconds)
       改成 s = int(seconds) // 1000 即可。"""
    if not seconds:
        return "—"
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_rank_prefix(player: dict) -> str:
    staff = player.get("rank")
    if staff and staff not in ("NORMAL", "NONE"):
        return f"[{staff}] "
    if player.get("monthlyPackageRank") == "SUPERSTAR":
        return "[MVP++] "
    rank = player.get("newPackageRank") or player.get("packageRank") or "NONE"
    return {
        "MVP_PLUS": "[MVP+] ",
        "MVP": "[MVP] ",
        "VIP_PLUS": "[VIP+] ",
        "VIP": "[VIP] ",
    }.get(rank, "")


def _wins_or_best(z: dict, m: str, diff: str) -> str:
    w = _g(z, f"wins_zombies_{m}_{diff}")
    if w:
        return str(w)
    w6 = _g(z, f'best_round_zombies_{m}_{diff}')
    if w6:
        return f"[{w6}]"
    return f"-"


def _wins_or_best_aa(z: dict) -> str:
    w = _g(z, "wins_zombies_alienarcadium")
    if w:
        return str(w)
    w6 = _g(z, "best_round_zombies_alienarcadium")
    if w6:
        return f"[{w6}]"
    return f"-"


def format_overall(z: dict, disp_name: str) -> str:
    total_rounds = _g(z, "total_rounds_survived_zombies")
    wins = _g(z, "wins_zombies")
    hit = _g(z, "bullets_hit_zombies")
    shot = _g(z, "bullets_shot_zombies")
    heads = _g(z, "headshots_zombies")
    acc = round(hit / shot * 100, 1) if shot else 0.0
    hsr = round(heads / hit * 100, 1) if hit else 0.0

    lines = [
        "===僵尸末日全局信息===",
        f"{disp_name} \n| 生存总回合: {_n(total_rounds)} \n| 胜场: {_n(wins)} \n"
        f"| 命中率: {acc}%  \n| 爆头率 {hsr}%",
        "| 胜场或最佳回合 (普通/困难/安息):",
    ]
    seg = []
    for m, cn in MAP_CN.items():
        seg.append(f"| ")
        if m == "alienarcadium":
            seg.append(f"{cn}: {_wins_or_best_aa(z)} \n")
        else:
            n_ = _wins_or_best(z, m, "normal")
            h_ = _wins_or_best(z, m, "hard")
            r_ = _wins_or_best(z, m, "rip")
            seg.append(f"{cn}: {n_}/{h_}/{r_} \n")
    lines.append("".join(seg))
    return "\n".join(lines)


def format_map_detail(z: dict, m: str, raw_name: str, diff: str = "normal") -> str:
    if m == "alienarcadium":
        diff = "normal"  

    cn = MAP_CN[m]
    map_label = cn if diff == "normal" else f"{cn}（{DIFF_CN[diff]}）"

    total_rounds = _g(z, f"total_rounds_survived_zombies_{m}")
    wins = _g(z, f"wins_zombies_{m}")
    best = _g(z, f"best_round_zombies_{m}")
    kills = _g(z, f"zombie_kills_zombies_{m}")
    revived = _g(z, f"players_revived_zombies_{m}")
    doors = _g(z, f"doors_opened_zombies_{m}")
    windows = _g(z, f"windows_repaired_zombies_{m}")
    knocked = _g(z, f"times_knocked_down_zombies_{m}")
    deaths = _g(z, f"deaths_zombies_{m}")

    t10 = fmt_time(_g(z, f"fastest_time_10_zombies_{m}_{diff}"))
    t20 = fmt_time(_g(z, f"fastest_time_20_zombies_{m}_{diff}"))
    clear = CLEAR_ROUND[m]
    t_clear = fmt_time(_g(z, f"fastest_time_30_zombies_{m}_{diff}"))

    lines = [
        f"{raw_name}",
        f"| 地图: {map_label}",
        f"| 生存总回合数: {_n(total_rounds)}",
        f"| 胜场: {_n(wins)}",
        f"| 最佳回合: {best}",
        f"| 僵尸击杀数: {_n(kills)}",
        f"| 复活玩家数: {_n(revived)}",
        f"| 开门数: {doors}",
        f"| 窗户修复数: {windows}",
        f"| 被击倒次数: {knocked}",
        f"| 死亡数: {deaths}",
        f"| 最快完成 10 回合: {t10}",
        f"| 最快完成 20 回合: {t20}",
        f"| 最快通关: {t_clear}",
    ]
    line1 = "\n".join(lines)
    out = ["===僵尸末日信息===", line1]

    boss_parts = [f"{label}: {_n(_g(z, field))}" for label, field in MAP_BOSSES.get(m, [])]
    for i in range(0, len(boss_parts), 2):
        out.append(" | ".join(boss_parts[i:i + 2]))

    return "\n".join(out)


@register("hypixel_zombies", "你的名字", "Hypixel Zombies 数据查询（直连官方 v2 API）", "1.2.0")
class ZombiesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.key = config.get("hypixel_key", "")

    async def _get_uuid(self, session: aiohttp.ClientSession, name: str) -> str:
        try:
            async with session.get(
                f"https://api.mojang.com/users/profiles/minecraft/{name}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    if data and data.get("id"):
                        return data["id"]
        except Exception:
            pass
        async with session.get(
            f"https://playerdb.co/api/player/minecraft/{name}",
            headers={"User-Agent": "astrbot-zombies/1.0"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            data = await r.json(content_type=None)
            if "data" not in data:
                raise RuntimeError(f"找不到玩家: {name}")
            return data["data"]["player"]["raw_id"]

    async def _get_player(self, session: aiohttp.ClientSession, uuid: str) -> dict:
        async with session.get(
            "https://api.hypixel.net/v2/player",
            params={"uuid": uuid},
            headers={"API-Key": self.key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            try:
                data = await r.json(content_type=None)
            except Exception:
                txt = await r.text()
                raise RuntimeError(f"Hypixel 返回非 JSON (HTTP {r.status}): {txt[:120]}")
        if not data.get("success"):
            raise RuntimeError(f"Hypixel 报错: {data.get('cause', '未知')}")
        if data.get("player") is None:
            raise RuntimeError("该玩家没有数据（可能从没进过服）。")
        return data["player"]

    @filter.command("zb")
    async def zb(self, event: AstrMessageEvent):
        '''Hypixel Zombies 查询。
        用法:
          /zb 玩家名                 -> 全局信息
          /zb 玩家名 aa              -> 单图详情(可多图: de bb aa pr)
          /zb 玩家名 de hard         -> 指定难度(normal默认/hard/rip, 跟在地图后)
          /zb 玩家名 dump [关键词]   -> 列出字段(默认击杀类; dump fastest 看时间字段)'''
        if not self.key:
            yield event.plain_result("还没配置 Hypixel API Key，去插件配置里填一下。")
            return

        parts = event.message_str.strip().split()
        if parts and parts[0].lstrip("/").lower() == "zb":
            parts = parts[1:]
        if not parts:
            yield event.plain_result("用法: /zb 玩家名 [de [hard] bb pr aa]  |  /zb 玩家名 dump")
            return

        name = parts[0]
        rest = [p.lower() for p in parts[1:]]

        try:
            async with aiohttp.ClientSession() as s:
                uuid = await self._get_uuid(s, name)
                player = await self._get_player(s, uuid)
        except Exception as e:
            logger.exception("zombies 查询失败")
            yield event.plain_result(f"查询出错: {e}")
            return

        arcade = player.get("stats", {}).get("Arcade", {})
        if not arcade:
            yield event.plain_result(f"{name} 没有 Zombies 数据。")
            return

        disp = get_rank_prefix(player) + player.get("displayname", name)
        raw_name = player.get("displayname", name)

        # 字段探测：默认击杀类；/zb 玩家 dump fastest 可看时间字段，dump wins 看胜场字段
        if rest and rest[0] in ("dump", "raw", "keys"):
            flt = rest[1] if len(rest) > 1 else "kills_zombies"
            keys = sorted(k for k in arcade if flt in k)
            text = f"【含 '{flt}' 的字段 ({len(keys)})】\n" + "\n".join(keys)
            yield event.plain_result(text[:3500])
            return

        map_diffs = []  # [[map, diff], ...]
        for a in rest:
            if a in MAP_ALIAS:
                map_diffs.append([MAP_ALIAS[a], "normal"])
            elif a in MAP_CN:
                map_diffs.append([a, "normal"])
            elif a in DIFF_ALIAS and map_diffs:
                map_diffs[-1][1] = DIFF_ALIAS[a]
           

        if not map_diffs:
            yield event.plain_result(format_overall(arcade, disp))
        else:
            blocks = [format_map_detail(arcade, m, raw_name, diff) for m, diff in map_diffs]
            yield event.plain_result("\n\n".join(blocks))

    async def terminate(self):
        pass

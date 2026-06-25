import aiohttp

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

MAP_ALIAS = {
    "de": "deadend",
    "bb": "badblood",
    "aa": "alienarcadium",
    "pr": "prison",
}
MAP_LABEL = {
    "deadend": "Dead End",
    "badblood": "Bad Blood",
    "alienarcadium": "Alien Arcadium",
    "prison": "Prison",
}


def _g(d, key, default=0):
    return d.get(key, default)


def format_overall(z: dict, name: str) -> str:
    wins = _g(z, "wins_zombies")
    kills = _g(z, "zombie_kills_zombies")
    deaths = _g(z, "deaths_zombies")
    best = _g(z, "best_round_zombies")
    hit = _g(z, "bullets_hit_zombies")
    shot = _g(z, "bullets_shot_zombies")
    revived = _g(z, "players_revived_zombies")
    knocked = _g(z, "times_knocked_down_zombies")
    kd = round(kills / deaths, 2) if deaths else kills
    acc = round(hit / shot * 100, 1) if shot else 0.0
    return (
        f"【{name}】Zombies 总览\n"
        f"胜场: {wins}   最高轮: {best}\n"
        f"总击杀: {kills}   死亡: {deaths}   K/D: {kd}\n"
        f"命中率: {acc}%   救人: {revived}   被击倒: {knocked}"
    )



def format_map(z: dict, m: str) -> str:
    label = MAP_LABEL[m]
    wins = _g(z, f"wins_zombies_{m}")
    best = _g(z, f"best_round_zombies_{m}")
    best_n = _g(z, f"best_round_zombies_{m}_normal")
    best_h = _g(z, f"best_round_zombies_{m}_hard")
    best_r = _g(z, f"best_round_zombies_{m}_rip")
    kills = _g(z, f"zombie_kills_zombies_{m}")
    deaths = _g(z, f"deaths_zombies_{m}")
    rounds = _g(z, f"total_rounds_survived_zombies_{m}")
    kd = round(kills / deaths, 2) if deaths else kills
    return (
        f"  · {label}\n"
        f"    胜场:{wins}  最高轮:{best}(普通:{best_n}, 困难:{best_h}, 安息:{best_r})\n"
        f"    击杀:{kills}  死亡:{deaths}  K/D:{kd}  累计存活轮:{rounds}"
    )


@register("hypixel_zombies", "你的名字", "Hypixel Zombies 数据查询（直连官方 v2 API）", "1.0.0")
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
                raise RuntimeError(
                    f"Hypixel 返回非 JSON (HTTP {r.status}): {txt[:120]}"
                )
        if not data.get("success"):
            raise RuntimeError(f"Hypixel 报错: {data.get('cause', '未知')}")
        if data.get("player") is None:
            raise RuntimeError("该玩家没有数据（可能从没进过服）。")
        return data["player"]

    @filter.command("zb")
    async def zb(self, event: AstrMessageEvent):
        '''查询 Hypixel Zombies 数据。用法: /zb 玩家名 [de bb aa pr]'''
        if not self.key:
            yield event.plain_result("还没配置 Hypixel API Key，去插件配置里填一下。")
            return

        parts = event.message_str.strip().split()
        if parts and parts[0].lstrip("/").lower() == "zb":
            parts = parts[1:]
        if not parts:
            yield event.plain_result("用法: /zb 玩家名 [de bb aa pr]")
            return

        name = parts[0]
        map_args = parts[1:]

        try:
            async with aiohttp.ClientSession() as s:
                uuid = await self._get_uuid(s, name)
                player = await self._get_player(s, uuid)
        except Exception as e:
            logger.exception("zombies 查询失败")
            yield event.plain_result(f"查询出错: {e}")
            return

        real_name = player.get("displayname", name)
        arcade = player.get("stats", {}).get("Arcade", {})
        if not arcade:
            yield event.plain_result(f"{real_name} 没有 Zombies 数据。")
            return

        lines = [format_overall(arcade, real_name)]
        maps = []
        for a in map_args:
            a = a.lower()
            if a in MAP_ALIAS:
                maps.append(MAP_ALIAS[a])
            elif a in MAP_LABEL:
                maps.append(a)
        if maps:
            lines.append("\n:")
            for m in maps:
                lines.append(format_map(arcade, m))

        yield event.plain_result("\n".join(lines))

    async def terminate(self):
        pass


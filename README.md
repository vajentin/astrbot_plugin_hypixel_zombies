# astrbot_plugin_hypixel_zombies

一个用于 AstrBot 的 Hypixel Zombies 数据查询插件，可查询玩家在 Hypixel 僵尸末日小游戏中的相关统计数据。

## 功能介绍

本插件可以查询 Hypixel Zombies 玩家数据，包括：

* 总生存回合数
* 胜场数
* 最佳回合
* 僵尸击杀数
* 复活玩家数
* 开门数
* 窗户修复数
* 被击倒次数
* 死亡数
* 各地图最快完成时间
* Boss 击杀统计

支持不同 Zombies 地图的数据展示，即仿axt机器人格式。

## 安装方法

进入 AstrBot 插件目录：

```bash
cd AstrBot/data/plugins
```

克隆本仓库：

```bash
git clone https://github.com/vajentin/astrbot_plugin_hypixel_zombies.git
```

## 配置说明

插件需要使用 Hypixel API Key 才能查询玩家数据。

请在 AstrBot 插件配置中填写你的 Hypixel API Key。

Hypixel API Key 可以在 Hypixel Developer Dashboard 中创建。

## 使用方法

在聊天中发送指令查询玩家 Zombies 数据：

```text
/zb 玩家名
```

示例：

```text
/zb Steve
```

插件会返回该玩家的 Zombies 总体数据或指定地图数据。

插件支持地图参数，可以使用类似格式：

```text
/zombies 玩家名 地图名
```

示例：

```text
/zombies Steve de/bb/aa/pr
```


## 注意事项

* 本插件依赖 Hypixel API，查询结果取决于 Hypixel 官方接口返回的数据。
* 如果玩家不存在、未玩过 Zombies，或 API 数据缺失，部分字段可能显示为空、0 或默认值。
* 如果 Hypixel API Key 无效，插件将无法正常查询数据。
* 请不要公开泄露自己的 Hypixel API Key。

## License

本项目仅供学习和交流使用。

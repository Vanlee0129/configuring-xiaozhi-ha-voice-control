# 通过 HA MCP Server 配置小智语音控制

一个 Claude Code 技能，用于配置 [小智 ESP32](https://github.com/78/xiaozhi-esp32) 通过 Home Assistant MCP Server 语音控制智能家居设备。

## 这个技能做什么

当你对 Claude Code 说"帮我配置小智语音控制家里的设备"时，它会：

1. **扫描** HA 中所有可控设备（空调、扫地机、电视、音箱、洗衣机等）
2. **创建** 必要的自定义组件（如 IR 空调的 `ir_climate` 组件）
3. **生成** 没有内置 intent 的操作所需的 script
4. **配置** 实体暴露、中文别名、区域分配（通过 HA websocket API）
5. **验证** 通过 conversation API 测试所有语音指令

## 支持的设备

| 设备 | 控制方式 | 语音指令 |
|------|---------|---------|
| 红外空调 | 自定义 climate ���体 | 开关、温度、模式 |
| 扫拖机器人 | 内置 intent + script | 开始扫地、停止、回充、洗拖布、烘干 |
| 电视/媒体播放器 | 内置 intent | 开关、暂停、音量 |
| 洗衣机/烘干机 | Script | 开始、暂停、停止 |
| 开关类设备 | 内置 intent | 开关 |
| 灯光 | 内置 intent | 开关 |

## 安装

### 作为 Claude Code 技能

```bash
# 克隆到 Claude Code 技能目录
git clone https://github.com/Vanlee0129/configuring-xiaozhi-ha-voice-control.git \
  ~/.claude/skills/configuring-xiaozhi-ha-voice-control
```

安装后，当你在 Claude Code 中提到小智语音控制或 HA 设备配置时，技能会自动激活。

### 前置条件

- Home Assistant 已安装 [MCP Server](https://www.home-assistant.io/integrations/mcp_server/) 集成
- 已安装 [xiaozhi-mcp-ha](https://github.com/mac8005/xiaozhi-mcp-ha) 自定义组件（桥接小智云 ↔ HA MCP Server）
- 小米智能家庭集成（含红外遥控器，用于空调控制）
- 小智 ESP32 设备已连接小智云

## 解决的关键问题

这个技能编码了实际调试中发现的 10 个常见坑：

1. button 实体不支持 HassTurnOn/Off intent
2. 多个实体共享别名导致 DUPLICATE_NAME
3. 手动编辑 `.storage/` 文件无效
4. 华氏度单位系统导致温度转换错误
5. LLM 拆分设备名为 name+area 导致匹配失败
6. MCP Server 只暴露 IntentTool 和 ScriptTool
7. LLM 选错 tool（HassTurnOn vs HassVacuumStart）
8. 代理/VPN 阻断 Docker 容器 SSL
9. 重复安装的 MCP 插件导致不稳定
10. 实体未暴露给 conversation assistant

## 文件说明

- `SKILL.md` — 主技能文档，包含完整配置指南
- `climate-template.py` — 可复用的 IR 空调 climate 组件模板
- `README.md` — 英文说明
- `README_CN.md` — 中文说明

## 许可证

MIT

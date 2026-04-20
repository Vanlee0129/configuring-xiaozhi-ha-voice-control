[中文]https://github.com/Vanlee0129/configuring-xiaozhi-ha-voice-control/blob/main/README_CN.md
# Configuring Xiaozhi Voice Control via HA MCP Server

A Claude Code skill for setting up [Xiaozhi ESP32](https://github.com/78/xiaozhi-esp32) voice control of smart home devices through Home Assistant's MCP Server.

## What This Skill Does

When you tell Claude Code "help me set up Xiaozhi voice control for my devices", it will:

1. **Scan** your HA instance for controllable devices (AC, vacuum, TV, speakers, washer, etc.)
2. **Create** the necessary custom components (e.g., `ir_climate` for IR air conditioners)
3. **Generate** scripts for operations without built-in intents
4. **Configure** entity exposure, aliases, and areas via HA websocket API
5. **Verify** everything works through the conversation API

## Supported Devices

| Device | Control Method | Voice Commands |
|--------|---------------|----------------|
| IR Air Conditioners | Custom climate entity | On/off, temperature, mode |
| Robot Vacuum | Built-in intent + scripts | Start, stop, return, wash mop, dry |
| TV / Media Players | Built-in intent | On/off, pause, volume |
| Washer / Dryer | Scripts | Start, pause, stop |
| Switches (any) | Built-in intent | On/off |
| Lights | Built-in intent | On/off |

## Installation

### As a Claude Code Skill

```bash
# Clone to your Claude Code skills directory
git clone https://github.com/Vanlee0129/configuring-xiaozhi-ha-voice-control.git \
  ~/.claude/skills/configuring-xiaozhi-ha-voice-control
```

Then in Claude Code, the skill will automatically activate when you ask about Xiaozhi voice control or HA device configuration.

### Prerequisites

- Home Assistant with [MCP Server](https://www.home-assistant.io/integrations/mcp_server/) integration
- [xiaozhi-mcp-ha](https://github.com/mac8005/xiaozhi-mcp-ha) custom component installed (bridges Xiaozhi Cloud ↔ HA MCP Server)
- Xiaomi Home integration with IR remotes (for AC control)
- Xiaozhi ESP32 device connected to Xiaozhi Cloud

## Key Pitfalls Solved

This skill encodes solutions to 10 common pitfalls discovered through real-world debugging:

1. Button entities don't support HassTurnOn/Off intents
2. DUPLICATE_NAME when multiple entities share aliases
3. Manual `.storage/` edits are ignored by HA
4. Imperial unit system causes temperature conversion errors
5. LLM splits device names into name+area that don't match
6. MCP Server only exposes IntentTool and ScriptTool
7. LLM picks wrong tool (HassTurnOn vs HassVacuumStart)
8. Proxy/VPN blocks Docker container SSL
9. Duplicate MCP plugins cause instability
10. Entities not exposed to conversation assistant

## Files

- `SKILL.md` — Main skill document with complete guide
- `climate-template.py` — Reusable IR AC climate component

## License

MIT

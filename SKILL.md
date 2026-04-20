---
name: configuring-xiaozhi-ha-voice-control
description: Use when setting up Xiaozhi ESP32 voice control of smart home devices through Home Assistant MCP Server, or when Xiaozhi says it cannot find or control a device, or when HA Assist intent matching fails
---

# Configuring Xiaozhi Voice Control via HA MCP Server

## Overview

Enable voice control of smart home devices through the Xiaozhi ESP32 → Xiaozhi Cloud → HA MCP Server pipeline. Covers all device types: AC, vacuum, media players, switches, and any device needing script-based control.

## When to Use

- Setting up Xiaozhi voice control for any HA device
- Xiaozhi says "找不到设备" or "暂时无法控制"
- HA logs show `MatchFailedReason.ASSISTANT` or `DUPLICATE_NAME`
- Device exists in HA but voice commands don't work
- Need to add new device types to voice control

## Architecture

```
Xiaozhi ESP32 → Xiaozhi Cloud → xiaozhi_mcp plugin (WebSocket)
  → HA MCP Server (SSE) → AssistAPI
```

The `xiaozhi_mcp` plugin ([xiaozhi-mcp-ha](https://github.com/mac8005/xiaozhi-mcp-ha)) bridges Xiaozhi Cloud and HA's MCP Server.
  → IntentTool (HassTurnOn/Off, HassClimateSetTemperature, HassVacuumStart...)
  → ScriptTool (any script exposed to conversation)
```

**Key constraint:** MCP Server ONLY exposes `IntentTool` and `ScriptTool`. No arbitrary service calls. If a device operation has no built-in intent, you MUST create a script.

## Device Strategy Matrix

| Device Domain | Built-in Intents | Needs Script For |
|---|---|---|
| climate | HassTurnOn/Off, HassClimateSetTemperature | set_hvac_mode (no intent exists) |
| vacuum | HassVacuumStart, HassVacuumReturnToBase | wash mop, dry mop, dust collect |
| media_player | HassMediaPause/Unpause, HassSetVolume | — |
| switch | HassTurnOn/Off | — |
| light | HassTurnOn/Off | — |
| button | NONE (not supported by any intent) | ALL operations need script |
| number | NONE | ALL operations need script |
| select | NONE | ALL operations need script |

## Pitfall Quick Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| "找不到设备" | Entity not exposed to conversation | `homeassistant/expose_entity` via websocket |
| DUPLICATE_NAME | Multiple entities share alias | Only ONE entity per alias |
| Temperature 26→-3°C | Unit system is imperial | `config/core/update` → metric |
| name+area mismatch | Entity missing area or area alias | Add area + short alias + generic device alias |
| HassTurnOn fails | Domain not supported (button) | Wrap in supported domain or create script |
| No set_hvac_mode | No built-in intent | Create script |
| LLM picks wrong tool | HassTurnOn vs HassVacuumStart | Create script with explicit name |
| WebSocket timeout | Proxy blocking Docker SSL | Disable proxy for api.xiaozhi.me |
| Manual .storage edit ignored | HA doesn't load manual edits | Always use websocket API |
| tools/call never arrives | Plugin disconnected | Check logs, `services/xiaozhi_mcp/reconnect` |

## Implementation Steps

### Step 1: Inventory Devices

```bash
# List all controllable entities
docker exec homeassistant python3 -c "
import json
with open('/config/.storage/core.entity_registry') as f:
    data = json.load(f)
domains = {}
for e in data['data']['entities']:
    d = e['entity_id'].split('.')[0]
    if d in ('climate','vacuum','media_player','switch','light','button','number','select'):
        domains.setdefault(d, []).append(e['entity_id'])
for d, ents in sorted(domains.items()):
    print(f'{d}: {len(ents)} entities')
"
```

### Step 2: Handle IR AC (if applicable)

IR ACs expose only `button`/`number`/`select` entities — none of which have built-in intents. Solution: create a custom `climate` entity wrapper.

Use `climate-template.py` (supporting file). Create:
- `custom_components/ir_climate/__init__.py` — `"""IR Climate."""`
- `custom_components/ir_climate/manifest.json` — see template
- `custom_components/ir_climate/climate.py` — from template

IR entity naming pattern (Xiaomi):
```
button.miir_cn_ir_{DEVICE_ID}_ir02_turn_on_a_2_6
button.miir_cn_ir_{DEVICE_ID}_ir02_turn_off_a_2_5
number.miir_cn_ir_{DEVICE_ID}_ir02_ir_temperature_p_2_2
select.miir_cn_ir_{DEVICE_ID}_ir02_ir_mode_p_2_1
```

### Step 3: Create Scripts for Unsupported Operations

Any operation without a built-in intent needs a script:

```yaml
# scripts.yaml examples:

# AC mode (no HassSetHvacMode intent)
shufang_ac_cool:
  alias: "书房空调制冷模式"
  sequence:
    - service: climate.set_hvac_mode
      target: {entity_id: climate.xxx}
      data: {hvac_mode: cool}

# Vacuum advanced ops (only start/return_to_base have intents)
robot_wash_mop:
  alias: "扫地机洗拖布"
  sequence:
    - service: button.press
      target: {entity_id: button.xxx_start_mop_wash_a_2_6}

# Washer/dryer (button domain, no intents)
washer_start:
  alias: "开始洗衣"
  sequence:
    - service: button.press
      target: {entity_id: button.xxx_start_wash_a_2_2}

# Vacuum start (fallback for LLM choosing HassTurnOn)
robot_start:
  alias: "开始扫地"
  sequence:
    - service: vacuum.start
      target: {entity_id: vacuum.xxx}
```

### Step 4: Expose Entities via Websocket API

**NEVER edit `.storage/` files directly.** Use websocket API:

```python
# Connect and auth
ws = websockets.connect('ws://localhost:8123/api/websocket')
# ... auth ...

# Expose entity
{"type": "homeassistant/expose_entity", "assistants": ["conversation"],
 "entity_ids": ["climate.xxx", "script.xxx"], "should_expose": true}

# Add aliases (Chinese name + generic name for area matching)
{"type": "config/entity_registry/update", "entity_id": "climate.xxx",
 "aliases": ["书房空调", "空调"]}

# Assign area
{"type": "config/entity_registry/update", "entity_id": "climate.xxx",
 "area_id": "jing_nan_tang_shu_fang"}

# Add area short alias (for LLM splitting "主卧空调" → name="空调" area="主卧")
{"type": "config/area_registry/update", "area_id": "jing_nan_tang_zhu_wo",
 "aliases": ["主卧"]}

# Clear conflicting aliases from other entities
{"type": "config/entity_registry/update", "entity_id": "button.xxx",
 "aliases": []}
```

### Step 5: Ensure Metric Units

```python
{"type": "config/core/update", "unit_system": "metric"}
```

### Step 6: Verify

```bash
TOKEN="your_token"
# Test via conversation API
curl -s -X POST http://localhost:8123/api/conversation/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"打开书房空调","language":"zh-cn"}'

# Check MCP connection
docker logs homeassistant --tail 50 | grep "xiaozhi_mcp"
# Should see: ping/pong every 30s, no "handshake timed out"

# If disconnected:
curl -X POST http://localhost:8123/api/services/xiaozhi_mcp/reconnect \
  -H "Authorization: Bearer $TOKEN"
```

## Common Mistakes

1. **Editing `.storage/` files** — HA overwrites them. Always use websocket API.
2. **Forgetting generic alias** — LLM splits "主卧空调" into name="空调" area="主卧". Entity needs BOTH "主卧空调" AND "空调" as aliases.
3. **Multiple entities same alias** — Only ONE entity should match a given name in a given area.
4. **Missing script for button operations** — button domain has NO intents. Every button operation needs a script wrapper.
5. **Proxy blocking Docker SSL** — Test: `docker exec homeassistant python3 -c "import urllib.request; urllib.request.urlopen('https://api.xiaozhi.me', timeout=5)"`
6. **Duplicate MCP plugins** — Only one xiaozhi_mcp plugin should be active. Check with: `curl http://localhost:8123/api/config/config_entries/entry | grep xiaozhi`

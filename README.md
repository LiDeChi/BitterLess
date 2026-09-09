# BitterLess

东周实验室：多层心智—模型—世界系统。

机器为了理解心智，长出一个研究所；研究所为了形成理论，逐步把东周展开；人物在展开出来的世界里形成自己的历史，而这些历史又反过来改变机器对心智的理解。

## 文档

- [`docs/original-zh.md`](docs/original-zh.md) — 架构口述原文（verbatim）
- [`docs/architecture.md`](docs/architecture.md) — 整理后的架构总览

## Phase 1 状态

可运行的垂直切片：研究所 Research Thread + 多尺度东周种子世界 + 信息压缩 + 时间线 fork + CLI/可选 Web demo。

### 已实现

1. **研究所 + Research Thread**：主研究员持续循环 `问题→模型→异常→假设→聚焦→高分辨率展开→证据→修改模型→新问题`；玩家可质疑假设 / 改变聚焦，而非逐步遥控。
2. **多尺度世界**：低分辨率近似整体；聚焦在人物/关系/媒介/行为/制度/时间/经济等维度展开高分辨率；高分辨率经**条件机制**回写低分辨率（禁止标签刻板印象）。
3. **人物 = 媒介流**：`raw → event → episode → pattern → belief` 压缩；死亡后媒介残留；**复显**仅基于 hard facts / 粗历史 / 当前状态，并标记 `reconstruction`。
4. **资源 = 分辨率预算**：降分辨率，不删人。
5. **时间线**：Canonical History 仅追加；Experimental Branch 可 fork；Sandbox 独立。
6. **种子场景**：四人小邑、两种媒介、一个形成中的里社。
7. **Demo**：CLI（`bitterless`）与可选最小 Web（`bitterless-web`）。

## 安装

需要 Python 3.11+。

```bash
cd BitterLess
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 运行 Demo

一条命令跑完整研究循环（对种子世界）：

```bash
bitterless
# 或
python -m bitterless.demo.cli
```

常用选项：

```bash
bitterless --cycles 2
bitterless --challenge "或许关键的是媒介重复而非债务本身"
bitterless --change-focus medium,institution
bitterless --remanifest 商氏
bitterless --smoke          # CI 友好短输出
bitterless --json           # 打印 CycleResult JSON
```

可选 Web UI：

```bash
bitterless-web --port 8765
# classic http://127.0.0.1:8765/
# 3D page  http://127.0.0.1:8765/institute/
```


## 3D Institute

Navigable WebGL institute (research desk, sealed model room, xianying photo wall, bamboo slips + sand table).

```bash
bitterless-web --port 8765
# open /institute/  (live state at /api/state , POST /api/cycle)
```

Controls: WASD move, drag to look, click objects for provenance.
Assets: src/bitterless/web/static/institute/

## 测试

```bash
pytest -q
```

覆盖：压缩阶梯、Canonical append-only、复显不变量、研究循环 smoke。

## 包布局

```
src/bitterless/
  models/          # types, compression, timeline, resources, world
  institute/       # researcher thread + research cycle
  seed/            # Eastern Zhou micro-seed
  demo/cli.py      # CLI
  web/app.py       # stdlib web + 3D institute + /api/*
  web/static/      # institute 3D assets
tests/
docs/
```

# 🐺 SwarmClaw - Multi-Agent Collaboration Engine
基于 OpenClaw 的多智能体协作实验平台 

# ✨ 这是什么？

SwarmClaw 是一个基于飞书的多智能体轻量化插件，可以实现多个智能体的“自主推进、自主协商、自主完成”各类复杂任务。  

# 🎬 视频演示

| 狼人杀 🐺 | 健身助手 💪 | 场馆预约 🏟️ |
|:---:|:---:|:---:|
| [🎬 点击观看](videos/狼人杀30秒gif.mp4) | [🎬 点击观看](videos/健身助手30秒gif.mp4) | [🎬 点击观看](videos/场馆预约30秒gif.mp4) |


# 🌲 Examples 案例代码

web应用开发案例代码位于 `examples/` 目录，每个子文件夹对应一个完整的团队配置示例：

- [`examples/book-rent/`](examples/book-rent/) — 图书借阅系统代码
- [`examples/sports-booking/`](examples/sports-booking/) — 体育场馆预约系统代码

# 🖥️ 架构图
---------
|xxx.png|
---------


💡 核心理念："群体智能涌现"--AI协作“三大自主”
   - 自主推进 (Autonomous Progression)：Agent 能够根据目标自动拆解阶段，无需用户一步步下指令。
   - 自主协商 (Autonomous Negotiation)：不同角色（如 PM 与 Coder）在群聊中自动对齐需求，解决冲突。
   - 自主完成 (Autonomous Completion)：最终交付可运行的产物，如代码包、分析报告或数据清单。  
  
# 🧩 特性
- 🧠 人格注入系统：一行命令为 AI 注入“求是SKILL”“第一性原理”或你自己调校的人设。
- 👥 多场景覆盖：任意角色组队，可在飞书群完成调研、决策、谈判、头脑风暴。
- 🔌 一行接入飞书：零侵入现有工作群，机器人即拉即用。

# 🚀 install
## 第一步：安装 OpenClaw

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
````

## 第二步：安装飞书插件

```bash
npx -y @larksuite/openclaw-lark install
```

## 第三步：安装 SwarmClaw

下载当前仓库中的 `openclaw-lark.zip`，放到仓库根目录（与 `swarmclaw.sh` 同级）。

然后运行一体化部署脚本：

```bash
chmod +x swarmclaw.sh
./swarmclaw.sh
```

脚本会自动检测你的环境，并显示菜单：

```
╔══════════════════════════════════════════════╗
║           SwarmClaw — 一体化部署工具        ║
╚══════════════════════════════════════════════╝

[INFO] 正在检测运行环境...
[OK] openclaw CLI 已安装
[OK] project 项目目录已就绪

  1) 部署 AI 软件工厂团队  ✓ 就绪
  2) 安装与配置swarmclaw插件  ✓ 就绪
  3) 全部执行（先部署团队，再配置飞书）
  4) 退出
```

选择 `3` 即可一键完成部署。

## 第四步：在飞书开放平台创建 Agent 并绑定

1. 前往 [飞书开放平台](https://open.feishu.cn/) 创建相应的Agent应用，获取 App ID 和 App Secret
2. 在 OpenClaw 中完成飞书渠道绑定（使用飞书开放平台创建的 App ID 和 App Secret）

## 第五步：重启 OpenClaw

```bash
openclaw gateway restart
```

## 第六步：在飞书中开始使用

在飞书群中 @机器人 发送任务，Agent 团队自动协作推进！

---

# 🚀 quick start
1. **领取邀请码** → 访问 [幻境工坊](https://www.itswarmbee.com)，注册登录
2.下载对应的team的zip文件
3.本机一键配置
4.链接飞书
5.开始运行











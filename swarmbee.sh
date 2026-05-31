#!/usr/bin/env bash

# SwarmClaw — 一体化部署与管理脚本
# 融合 install.sh（部署 Agent 团队）和 setup-lark.sh（安装配置飞书插件）

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 智能探测项目目录：优先当前目录，其次 fallback 到 full-stack-agent-team 子目录
if [ -f "$SCRIPT_DIR/manifest.json" ]; then
  PROJECT_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/full-stack-agent-team/manifest.json" ]; then
  PROJECT_DIR="$SCRIPT_DIR/full-stack-agent-team"
else
  PROJECT_DIR=""  # 稍后在自检中提示
fi

OPENCLAW_JSON="$HOME/.openclaw/openclaw.json"
EXTENSIONS_DIR="$HOME/.openclaw/extensions"
LARK_DIR="$EXTENSIONS_DIR/openclaw-lark"
ZIP_FILE="$SCRIPT_DIR/openclaw-lark.zip"

LOG_FILE="$HOME/.openclaw/install.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TIMESTAMP_FOR_BACKUP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$SCRIPT_DIR/backup"
BACKUP_LARK_DIR="$BACKUP_DIR/openclaw-lark-$TIMESTAMP_FOR_BACKUP"

# 环境状态变量
HAS_OPENCLAW=false
HAS_LARK=false
HAS_OPENCLAW_JSON=false
HAS_JQ=false
HAS_MANIFEST=false

# ====================================================================
# 通用工具函数
# ====================================================================

fail() {
  echo -e "${RED}[ERROR]${NC} $1"
  exit 1
}

info() {
  echo -e "${CYAN}[INFO]${NC} $1"
}

ok() {
  echo -e "${GREEN}[OK]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

check_environment() {
  info "正在检测运行环境..."

  if command -v openclaw >/dev/null 2>&1; then
    HAS_OPENCLAW=true
    ok "openclaw CLI 已安装"
  else
    warn "openclaw CLI 未检测到"
  fi

  if command -v jq >/dev/null 2>&1; then
    HAS_JQ=true
    ok "jq 已安装"
  else
    warn "jq 未安装 (配置飞书插件需要)"
  fi

  if [[ -f "$OPENCLAW_JSON" ]]; then
    HAS_OPENCLAW_JSON=true
    ok "openclaw.json 已存在"
  else
    warn "openclaw.json 未找到 (配置飞书插件需要)"
  fi

  if [[ -d "$LARK_DIR" ]]; then
    HAS_LARK=true
    ok "飞书插件已安装"
  elif [[ -f "$ZIP_FILE" ]]; then
    warn "飞书插件未安装，但检测到 openclaw-lark.zip (可通过菜单安装)"
  else
    warn "飞书插件未安装，且未找到 openclaw-lark.zip"
  fi

  if [[ -n "$PROJECT_DIR" ]] && [[ -f "$PROJECT_DIR/manifest.json" ]]; then
    HAS_MANIFEST=true
    ok "项目目录已就绪: $PROJECT_DIR"
  else
    warn "未找到 manifest.json，请将脚本放在项目目录中运行"
    warn "期望路径: $SCRIPT_DIR/manifest.json 或 $SCRIPT_DIR/full-stack-agent-team/manifest.json"
  fi

  echo ""
}

print_environment_guide() {
  local need_guide=false

  if [[ "$HAS_OPENCLAW" != "true" ]]; then
    need_guide=true
  fi
  if [[ "$HAS_LARK" != "true" ]]; then
    need_guide=true
  fi
  if [[ "$HAS_OPENCLAW_JSON" != "true" ]]; then
    need_guide=true
  fi

  if [[ "$need_guide" != "true" ]]; then
    return
  fi

  echo -e "${YELLOW}==============================================${NC}"
  echo -e "${YELLOW}  部分依赖未就绪，以下是安装指引：${NC}"
  echo -e "${YELLOW}==============================================${NC}"
  echo ""

  if [[ "$HAS_OPENCLAW" != "true" ]]; then
    echo -e "  ${RED}✗${NC} OpenClaw 未安装，请先执行："
    echo ""
    echo -e "    ${CYAN}curl -fsSL https://openclaw.ai/install.sh | bash${NC}"
    echo ""
    echo -e "    安装完成后重新打开终端，再运行本脚本。"
    echo ""
  fi

  if [[ "$HAS_OPENCLAW" == "true" ]] && [[ "$HAS_OPENCLAW_JSON" != "true" ]]; then
    echo -e "  ${RED}✗${NC} openclaw.json 不存在，请先初始化 OpenClaw："
    echo ""
    echo -e "    ${CYAN}openclaw init${NC}"
    echo ""
  fi

  if [[ "$HAS_LARK" != "true" ]]; then
    if [[ -f "$ZIP_FILE" ]]; then
      echo -e "  ${RED}✗${NC} 飞书插件未安装，请在本脚本菜单中选择 ${CYAN}\"2) 安装与配置飞书插件\"${NC}"
    else
      echo -e "  ${RED}✗${NC} 飞书插件 (openclaw-lark.zip) 未找到"
      echo -e "    请从 LaaS 平台下载 openclaw-lark.zip 并放到本脚本同级目录"
    fi
    echo ""
  fi

  if [[ "$HAS_JQ" != "true" ]]; then
    echo -e "  ${RED}✗${NC} jq 未安装，配置飞书插件需要："
    echo ""
    echo -e "    ${CYAN}brew install jq${NC}"
    echo ""
  fi

  echo -e "${YELLOW}==============================================${NC}"
  echo ""
}

print_banner() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║           SwarmClaw — 一体化部署工具        ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

print_menu() {
  echo "请选择要执行的操作："
  echo ""

  if [[ "$HAS_MANIFEST" == "true" ]]; then
    echo -e "  ${CYAN}1${NC}) 部署 AI 软件工厂团队  ${GREEN}✓ 就绪${NC}"
  else
    echo -e "  ${CYAN}1${NC}) 部署 AI 软件工厂团队  ${RED}✗ 项目目录未找到${NC}"
  fi
  echo -e "     从 manifest.json 读取配置，创建 Agent 工作区、注入身份灵魂、安装技能"
  echo ""

  if [[ -f "$ZIP_FILE" ]] && [[ "$HAS_OPENCLAW" == "true" ]] && [[ "$HAS_OPENCLAW_JSON" == "true" ]]; then
    echo -e "  ${CYAN}2${NC}) 安装与配置飞书插件  ${GREEN}✓ 就绪${NC}"
  elif [[ "$HAS_LARK" == "true" ]]; then
    echo -e "  ${CYAN}2${NC}) 安装与配置飞书插件  ${GREEN}✓ 已安装 (可重新配置)${NC}"
  else
    echo -e "  ${CYAN}2${NC}) 安装与配置飞书插件  ${RED}✗ 缺少依赖${NC}"
  fi
  echo -e "     安装 openclaw-lark 扩展，配置 Agent 飞书名称、群聊 ID、协作参数"
  echo ""

  echo -e "  ${CYAN}3${NC}) 全部执行（先部署团队，再配置飞书）"
  echo ""

  echo -e "  ${CYAN}4${NC}) 退出"
  echo ""
}

# ====================================================================
# 模式 1：部署 Agent 团队（原 install.sh）
# ====================================================================

install_agent() {
  local agent_id="$1"
  local identity_source="$2"
  local skills="$3"
  local workspace_dir="$HOME/.openclaw/workspace-$agent_id"

  echo ""
  echo -e "${YELLOW}--------------------------------------------------${NC}"
  echo -e "🚀 正在部署角色: ${GREEN}$agent_id${NC}"

  if [ -d "$workspace_dir" ]; then
    echo -e "   📂 工作区已存在: $workspace_dir"
  else
    mkdir -p "$workspace_dir"
    echo -e "   ✅ 创建工作区: $workspace_dir"
  fi

  echo -e "   👤 注册 Agent..."
  openclaw agents add --workspace "$workspace_dir" "$agent_id" >/dev/null 2>&1 || true
  echo -e "   ✅ Agent 注册完成"

  echo -e "   🎭 注入身份..."

  if [ -f "$identity_source" ]; then
    cp "$identity_source" "$workspace_dir/IDENTITY.md"
    echo -e "   ✅ 身份注入 (IDENTITY.md): $(basename "$identity_source")"

  elif [ -d "$identity_source" ]; then
    if [ -f "$identity_source/AGENTS.md" ]; then
      cp "$identity_source/AGENTS.md" "$workspace_dir/AGENTS.md"
      echo -e "   ✅ 身份注入 (AGENTS.md)"
    fi

    if [ -f "$identity_source/SOUL.md" ]; then
      cp "$identity_source/SOUL.md" "$workspace_dir/SOUL.md"
      echo -e "   ✅ 灵魂注入 (SOUL.md)"
    fi

    if [ -d "$identity_source/skills" ]; then
      echo -e "   🛠️  安装内置技能..."
      cp -r "$identity_source/skills" "$workspace_dir/"
      echo -e "   ✅ 内置技能安装完成"
    fi
  else
    echo -e "   ⚠️  警告: 找不到身份文件/文件夹: $identity_source"
  fi

  if [ -n "$skills" ]; then
    echo -e "   🛠️  安装外部技能..."
    IFS=',' read -ra SKILL_ARRAY <<< "$skills"
    for skill in "${SKILL_ARRAY[@]}"; do
      skill=$(echo "$skill" | tr -d ' ')
      if [ -n "$skill" ]; then
        echo -e "   📦 安装技能: $skill"
        openclaw skills install "$skill" --workspace "$workspace_dir" >/dev/null 2>&1 || true
        echo -e "   ✅ 技能处理完成: $skill"
      fi
    done
  fi

  echo -e "   📍 工作区路径: $workspace_dir"
}

mode_deploy_team() {
  echo ""
  echo -e "${BLUE}===> 准备启动【AI 全自动软件工厂】部署程序...${NC}"
  echo -e "   开始时间: ${TIMESTAMP}"

  OC_BASE_DIR="${OC_BASE_DIR:-$HOME/.openclaw}"
  DATA_DIR="$PROJECT_DIR/data"

  if [ ! -f "$PROJECT_DIR/manifest.json" ]; then
    fail "错误: 找不到 manifest.json 文件 (期望路径: $PROJECT_DIR/manifest.json)"
  fi

  if [ ! -d "$DATA_DIR" ]; then
    fail "错误: 找不到 data 目录 (期望路径: $DATA_DIR)"
  fi

  agents_data=$(python3 -c "
import json, os

with open('$PROJECT_DIR/manifest.json') as f:
    data = json.load(f)
    for a in data.get('agents', []):
        agent_id = a.get('id', '')
        identity_file = a.get('file', '')
        skills = ','.join(a.get('skills', []))

        identity_path = os.path.join('$PROJECT_DIR/data', identity_file)
        if os.path.isdir(identity_path):
            id_type = 'dir'
        else:
            id_type = 'file'

        print(f\"{agent_id}|{identity_file}|{skills}|{id_type}\")
" 2>/dev/null)

  if [ -z "$agents_data" ]; then
    fail "错误: 无法解析 manifest.json"
  fi

  echo "$agents_data" | while IFS="|" read -r agent_id identity_file skills id_type; do
    install_agent "$agent_id" "$PROJECT_DIR/data/$identity_file" "$skills"
  done

  echo ""
  echo -e "${YELLOW}--------------------------------------------------${NC}"
  echo -e "${GREEN}🎉 软件工厂团队已就绪！${NC}"
  echo ""
  echo -e "现在你可以尝试在飞书群里说："
  echo -e "${BLUE}  \"我们需要开发一个支持在线投票的小程序\"${NC}"
  echo -e "\n📝 日志文件: $LOG_FILE"
}

# ====================================================================
# 模式 2：安装与配置飞书插件（原 setup-lark.sh）
# ====================================================================

check_prerequisites() {
  info "正在检查运行前提..."

  command -v jq >/dev/null 2>&1 || fail "缺少 jq 命令，请先安装: brew install jq"

  if ! command -v python3 >/dev/null 2>&1; then
    fail "缺少 python3 命令"
  fi

  if [[ ! -f "$ZIP_FILE" ]]; then
    fail "未找到 openclaw-lark.zip，请确保此脚本与 openclaw-lark.zip 在同一目录"
  fi

  if [[ ! -f "$OPENCLAW_JSON" ]]; then
    fail "未找到 openclaw.json: $OPENCLAW_JSON"
  fi

  ok "前提检查通过 (jq / python3 / openclaw-lark.zip / openclaw.json)"
}

backup_existing_lark() {
  if [[ -d "$LARK_DIR" ]]; then
    info "正在备份现有 openclaw-lark 插件..."
    mkdir -p "$BACKUP_LARK_DIR"
    cp -R "$LARK_DIR"/* "$BACKUP_LARK_DIR"/ 2>/dev/null || true
    ok "已备份到: $BACKUP_LARK_DIR"
  else
    info "未发现现有 openclaw-lark 插件，跳过备份。"
  fi
}

install_lark() {
  info "正在解压 openclaw-lark.zip 到 $EXTENSIONS_DIR ..."
  mkdir -p "$EXTENSIONS_DIR"
  unzip -o "$ZIP_FILE" -d "$EXTENSIONS_DIR" >/dev/null
  ok "openclaw-lark 已安装/更新完成。"
}

get_agent_ids() {
  jq -r '.agents.list[]?.id // ""' "$OPENCLAW_JSON" 2>/dev/null | grep -v '^$' || true
}

get_agent_name() {
  local agent_id="$1"
  jq -r --arg id "$agent_id" '.agents.list[] | select(.id == $id) | .name // ""' "$OPENCLAW_JSON" 2>/dev/null
}

get_existing_game_group_ids() {
  jq -r '.channels.feishu.gameGroupIds[]? // ""' "$OPENCLAW_JSON" 2>/dev/null | grep -v '^$' || true
}

get_existing_handoff_field() {
  local key="$1"
  jq -r --arg key "$key" '.channels.feishu.agentHandoff[$key] // ""' "$OPENCLAW_JSON" 2>/dev/null
}

backup_openclaw_json() {
  local backup_path="$BACKUP_DIR/openclaw.json-$TIMESTAMP_FOR_BACKUP"
  mkdir -p "$BACKUP_DIR"
  cp "$OPENCLAW_JSON" "$backup_path"
  ok "openclaw.json 已备份到: $backup_path"
}

configure_agent_names() {
  echo ""
  info "=============================================="
  info "  1/3 配置智能体飞书显示名称"
  info "=============================================="
  echo ""

  local agent_ids=()
  while IFS= read -r id; do
    agent_ids+=("$id")
  done < <(get_agent_ids)

  if [[ ${#agent_ids[@]} -eq 0 ]]; then
    warn "未检测到任何智能体，跳过名称配置。"
    return
  fi

  info "检测到 ${#agent_ids[@]} 个智能体:"

  local agent_updates=""

  for agent_id in "${agent_ids[@]}"; do
    local current_name
    current_name="$(get_agent_name "$agent_id")"
    local hint=""
    if [[ -n "$current_name" ]]; then
      hint=" [当前: $current_name]"
    fi

    echo ""
    printf "  ${CYAN}%s${NC}%s\n" "$agent_id" "$hint"
    read -r -p "  请输入飞书显示名称 (回车保留当前值): " input_name

    local final_name="$input_name"
    if [[ -z "$final_name" ]]; then
      final_name="$current_name"
    fi

    if [[ -n "$final_name" ]]; then
      agent_updates="$agent_updates | .agents.list |= map(if .id == \"$agent_id\" then .name = \"$final_name\" else . end)"
    fi
  done

  if [[ -n "$agent_updates" ]]; then
    local tmp_json
    tmp_json="$(mktemp)"
    jq "$agent_updates" "$OPENCLAW_JSON" > "$tmp_json" 2>/dev/null
    mv "$tmp_json" "$OPENCLAW_JSON"
  fi

  ok "智能体飞书名称配置完成。"
}

configure_game_group_ids() {
  echo ""
  info "=============================================="
  info "  2/3 配置飞书群聊 ID (gameGroupIds)"
  info "=============================================="
  echo ""

  local existing_ids
  existing_ids="$(get_existing_game_group_ids)"

  if [[ -n "$existing_ids" ]]; then
    echo "  当前已有的群聊 ID:"
    echo "$existing_ids" | while read -r id; do
      echo "    - $id"
    done
    echo ""
  fi

  local game_group_ids=()
  local keep_going="y"

  while [[ "$keep_going" =~ ^[Yy]$ ]]; do
    read -r -p "  请输入飞书群聊 ID (输入空值结束): " group_id

    if [[ -z "$group_id" ]]; then
      break
    fi

    game_group_ids+=("$group_id")
    ok "已添加: $group_id"

    read -r -p "  是否继续添加? (y/n，默认 y): " keep_going
    keep_going="${keep_going:-y}"
  done

  if [[ ${#game_group_ids[@]} -gt 0 ]]; then
    local json_array=""
    for id in "${game_group_ids[@]}"; do
      if [[ -z "$json_array" ]]; then
        json_array="\"$id\""
      else
        json_array="$json_array, \"$id\""
      fi
    done

    local tmp_json
    tmp_json="$(mktemp)"
    jq ".channels.feishu.gameGroupIds = [$json_array]" "$OPENCLAW_JSON" > "$tmp_json" 2>/dev/null
    mv "$tmp_json" "$OPENCLAW_JSON"
    ok "已配置 ${#game_group_ids[@]} 个群聊 ID。"
  else
    info "未添加新的群聊 ID，跳过更新。"
  fi
}

configure_agent_handoff() {
  echo ""
  info "=============================================="
  info "  3/3 配置 agentHandoff 协作参数"
  info "=============================================="
  echo ""

  local DEFAULT_TASK_TEMPLATE="[System: 这是来自 {sourceDisplayName} 的 agent 协作任务。]\n\n[System: 当前系统协作深度 {handoffRound}/{maxRounds}。这只是系统限制，不是任务编号；若需要继续转交其他 agent，不得超过最大深度。]\n\n[System: 协作顺序、回执策略、汇总方式以当前 agent 的提示词/AGENTS 规则为准；基础收发能力与深度控制由系统负责。]\n\n{taskBody}"
  local DEFAULT_RECEIPT_TEMPLATE="协作任务已收到，开始处理。"
  local DEFAULT_COMPLETE_TEMPLATE="协作任务已处理完成，相关结果已发在群里。"
  local DEFAULT_FAILURE_TEMPLATE="协作任务处理失败，错误信息已回传。"

  local existing_max_rounds
  existing_max_rounds="$(get_existing_handoff_field "maxRounds")"

  local existing_auto_continue
  existing_auto_continue="$(get_existing_handoff_field "autoContinue")"

  local existing_stagger_ms
  existing_stagger_ms="$(get_existing_handoff_field "handoffStaggerMs")"

  local existing_receipt_template
  existing_receipt_template="$(get_existing_handoff_field "receiptTemplate")"

  echo "  以下参数有默认值，回车将使用推荐默认值。"
  echo ""

  local max_rounds_hint=""
  if [[ -n "$existing_max_rounds" ]]; then
    max_rounds_hint=" [当前值: $existing_max_rounds]"
  fi
  printf "  maxRounds (最大任务深度)%s\n" "$max_rounds_hint"
  read -r -p "  [默认: 100]: " max_rounds
  max_rounds="${max_rounds:-100}"

  local stagger_hint=""
  if [[ -n "$existing_stagger_ms" ]]; then
    stagger_hint=" [当前值: $existing_stagger_ms]"
  fi
  printf "  handoffStaggerMs (触发延迟毫秒)%s\n" "$stagger_hint"
  read -r -p "  [默认: 500]: " handoff_stagger_ms
  handoff_stagger_ms="${handoff_stagger_ms:-500}"

  local auto_continue_hint=""
  if [[ -n "$existing_auto_continue" ]]; then
    auto_continue_hint=" [当前值: $existing_auto_continue]"
  fi
  printf "  autoContinue (自动继续)%s\n" "$auto_continue_hint"
  read -r -p "  [默认: true]: " auto_continue
  auto_continue="${auto_continue:-true}"

  local receipt_hint=""
  if [[ -n "$existing_receipt_template" ]]; then
    receipt_hint=" [当前值: $existing_receipt_template]"
  fi
  printf "  receiptTemplate (回执模板)%s\n" "$receipt_hint"
  read -r -p "  [默认: ${DEFAULT_RECEIPT_TEMPLATE}]: " receipt_template
  receipt_template="${receipt_template:-$DEFAULT_RECEIPT_TEMPLATE}"

  echo ""

  local tmp_json
  tmp_json="$(mktemp)"

  python3 -c "
import json

with open('$OPENCLAW_JSON', 'r') as f:
    cfg = json.load(f)

cfg.setdefault('channels', {}).setdefault('feishu', {})

handoff = cfg['channels']['feishu'].get('agentHandoff') or {}
if not isinstance(handoff, dict):
    handoff = {}

handoff['maxRounds'] = int('$max_rounds')
handoff['autoReceipt'] = False
handoff['autoComplete'] = False
handoff['autoContinue'] = True if '$auto_continue'.lower() in ('true', '1', 'yes') else False
handoff['handoffStaggerMs'] = int('$handoff_stagger_ms')
handoff['taskTemplate'] = '''$DEFAULT_TASK_TEMPLATE'''
handoff['receiptTemplate'] = '''$receipt_template'''
handoff['completeTemplate'] = '''$DEFAULT_COMPLETE_TEMPLATE'''
handoff['failureTemplate'] = '''$DEFAULT_FAILURE_TEMPLATE'''

cfg['channels']['feishu']['agentHandoff'] = handoff

with open('$tmp_json', 'w') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
    f.write('\n')
"

  mv "$tmp_json" "$OPENCLAW_JSON"
  ok "agentHandoff 配置完成。"
}

print_handoff_summary() {
  echo ""
  info "=============================================="
  info "  agentHandoff 最终配置摘要"
  info "=============================================="
  echo ""

  echo "  channels.feishu.agentHandoff:"
  echo "  ┌─────────────────────────────────────────────"
  jq -r '.channels.feishu.agentHandoff | to_entries[] | "  │ \(.key): \(.value)"' "$OPENCLAW_JSON" 2>/dev/null || echo "  │ (无)"
  echo "  └─────────────────────────────────────────────"

  echo ""
  echo "  channels.feishu.gameGroupIds:"
  echo "  ┌─────────────────────────────────────────────"
  jq -r '.channels.feishu.gameGroupIds[]? | "  │ - \(.)"' "$OPENCLAW_JSON" 2>/dev/null || echo "  │ (无)"
  echo "  └─────────────────────────────────────────────"

  echo ""
  info "智能体名称列表:"
  echo "  ┌─────────────────────────────────────────────"
  jq -r '.agents.list[]? | "  │ \(.id): \(.name // "(无名称)")"' "$OPENCLAW_JSON" 2>/dev/null || echo "  │ (无)"
  echo "  └─────────────────────────────────────────────"
}

mode_setup_lark() {
  echo ""
  echo -e "${BLUE}===> 开始安装与配置飞书插件...${NC}"

  check_prerequisites

  backup_openclaw_json

  backup_existing_lark

  install_lark

  configure_agent_names

  configure_game_group_ids

  configure_agent_handoff

  print_handoff_summary

  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  全部配置完成！                              ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  info "备份文件位于: $BACKUP_DIR"
  info "建议重启 OpenClaw 或相关服务使配置生效。"
  echo ""
}

# ====================================================================
# 主流程
# ====================================================================

main() {
  print_banner
  check_environment
  print_environment_guide

  while true; do
    print_menu
    read -r -p "请输入选项 [1-4]: " choice
    echo ""

    case "$choice" in
      1)
        if [[ "$HAS_MANIFEST" != "true" ]]; then
          fail "项目目录未就绪，无法部署团队。请确保 manifest.json 与 swarmclaw.sh 在同一目录"
        fi
        mode_deploy_team
        break
        ;;
      2)
        if [[ "$HAS_OPENCLAW" != "true" ]]; then
          fail "OpenClaw 未安装，无法配置飞书插件。请先安装 OpenClaw"
        fi
        if [[ ! -f "$ZIP_FILE" ]] && [[ "$HAS_LARK" != "true" ]]; then
          fail "未找到 openclaw-lark.zip，请将其放在 swarmclaw.sh 同级目录"
        fi
        mode_setup_lark
        break
        ;;
      3)
        if [[ "$HAS_MANIFEST" != "true" ]]; then
          fail "项目目录未就绪，无法部署团队"
        fi
        mode_deploy_team
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}  团队部署完成，继续配置飞书插件...         ${NC}"
        echo -e "${GREEN}============================================${NC}"
        echo ""
        if [[ "$HAS_OPENCLAW" != "true" ]]; then
          warn "OpenClaw 未安装，跳过飞书插件配置"
          break
        fi
        if [[ ! -f "$ZIP_FILE" ]] && [[ "$HAS_LARK" != "true" ]]; then
          warn "未找到 openclaw-lark.zip，跳过飞书插件配置"
          break
        fi
        mode_setup_lark
        break
        ;;
      4)
        echo -e "${YELLOW}已退出。${NC}"
        exit 0
        ;;
      *)
        echo -e "${RED}无效选项，请重新选择。${NC}"
        echo ""
        ;;
    esac
  done
}

main
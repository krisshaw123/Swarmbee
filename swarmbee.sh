#!/usr/bin/env bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_JSON="$HOME/.openclaw/openclaw.json"
EXTENSIONS_DIR="$HOME/.openclaw/extensions"
LARK_DIR="$EXTENSIONS_DIR/openclaw-lark"
ZIP_FILE="$SCRIPT_DIR/openclaw-lark.zip"
BACKUP_DIR="$SCRIPT_DIR/backup"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_LARK_DIR="$BACKUP_DIR/openclaw-lark-$TIMESTAMP"

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
  local backup_path="$BACKUP_DIR/openclaw.json-$TIMESTAMP"
  mkdir -p "$BACKUP_DIR"
  cp "$OPENCLAW_JSON" "$backup_path"
  ok "openclaw.json 已备份到: $backup_path"
}

configure_agent_names() {
  set +e

  echo ""
  info "=============================================="
  info "  1/3 配置智能体飞书显示名称"
  info "=============================================="
  echo ""

  local agent_ids
  agent_ids=($(get_agent_ids))

  if [[ ${#agent_ids[@]} -eq 0 ]]; then
    warn "未检测到任何智能体，跳过名称配置。"
    set -e
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
    read -r -p "  请输入飞书显示名称 (回车保留当前值): " input_name </dev/tty

    local final_name="$input_name"
    if [[ -z "$final_name" ]]; then
      final_name="$current_name"
    fi

    if [[ -n "$final_name" ]]; then
      agent_updates="$agent_updates | .agents.list |= map(if .id == \"$agent_id\" then .name = \"$final_name\" else . end)"
    fi
  done

  if [[ -n "$agent_updates" ]]; then
    agent_updates="${agent_updates# | }"
    local tmp_json
    tmp_json="$(mktemp)"
    if ! jq "$agent_updates" "$OPENCLAW_JSON" > "$tmp_json" 2>/dev/null; then
      warn "jq 更新智能体名称失败，跳过该步骤。"
      rm -f "$tmp_json"
    else
      mv "$tmp_json" "$OPENCLAW_JSON"
    fi
  fi

  ok "智能体飞书名称配置完成。"
  set -e
}

configure_game_group_ids() {
  set +e

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
    read -r -p "  请输入飞书群聊 ID (输入空值结束): " group_id </dev/tty

    if [[ -z "$group_id" ]]; then
      break
    fi

    game_group_ids+=("$group_id")
    ok "已添加: $group_id"

    read -r -p "  是否继续添加? (y/n，默认 y): " keep_going </dev/tty
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
    if ! jq ".channels.feishu.gameGroupIds = [$json_array]" "$OPENCLAW_JSON" > "$tmp_json" 2>/dev/null; then
      warn "jq 更新群聊 ID 失败，跳过该步骤。"
      rm -f "$tmp_json"
    else
      mv "$tmp_json" "$OPENCLAW_JSON"
      ok "已配置 ${#game_group_ids[@]} 个群聊 ID。"
    fi
  else
    info "未添加新的群聊 ID，跳过更新。"
  fi
  set -e
}

configure_agent_handoff() {
  set +e

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

  # maxRounds
  local max_rounds_hint=""
  if [[ -n "$existing_max_rounds" ]]; then
    max_rounds_hint=" [当前值: $existing_max_rounds]"
  fi
  printf "  maxRounds (最大任务深度)%s\n" "$max_rounds_hint"
  read -r -p "  [默认: 100]: " max_rounds </dev/tty
  max_rounds="${max_rounds:-100}"

  # handoffStaggerMs
  local stagger_hint=""
  if [[ -n "$existing_stagger_ms" ]]; then
    stagger_hint=" [当前值: $existing_stagger_ms]"
  fi
  printf "  handoffStaggerMs (触发延迟毫秒)%s\n" "$stagger_hint"
  read -r -p "  [默认: 500]: " handoff_stagger_ms </dev/tty
  handoff_stagger_ms="${handoff_stagger_ms:-500}"

  # autoContinue
  local auto_continue_hint=""
  if [[ -n "$existing_auto_continue" ]]; then
    auto_continue_hint=" [当前值: $existing_auto_continue]"
  fi
  printf "  autoContinue (自动继续)%s\n" "$auto_continue_hint"
  read -r -p "  [默认: true]: " auto_continue </dev/tty
  auto_continue="${auto_continue:-true}"

  # receiptTemplate
  local receipt_hint=""
  if [[ -n "$existing_receipt_template" ]]; then
    receipt_hint=" [当前值: $existing_receipt_template]"
  fi
  printf "  receiptTemplate (回执模板)%s\n" "$receipt_hint"
  read -r -p "  [默认: ${DEFAULT_RECEIPT_TEMPLATE}]: " receipt_template </dev/tty
  receipt_template="${receipt_template:-$DEFAULT_RECEIPT_TEMPLATE}"

  echo ""

  local tmp_json
  tmp_json="$(mktemp)"

  python3 -c "
import json, sys

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
  set -e
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

main() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║       改进版OpenClaw Lark 安装与配置脚本          ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
  echo ""

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

main

#!/bin/bash
# 建立 3 個家人 agent profile：etf_wife, etf_son, etf_daughter
# 架構：skills/ + wiki/ 走 symlink，其餘各自獨立

set -uo pipefail

MASTER="$HOME/.hermes/profiles/etf_master"
PROFILE_BASE="$HOME/.hermes/profiles"

# === 清理舊的 etf_master_wife（空殼） ===
if [ -d "$PROFILE_BASE/etf_master_wife" ]; then
    echo "🧹 移除舊 etf_master_wife 空殼..."
    rm -rf "$PROFILE_BASE/etf_master_wife"
fi

create_profile() {
    local PROFILE_NAME="$1"
    local AGENT_NAME="$2"
    local TITLE="$3"
    local CALL="$4"
    
    local DIR="$PROFILE_BASE/$PROFILE_NAME"
    
    echo "=============================="
    echo "📋 建立 $AGENT_NAME — $TITLE"
    echo "=============================="
    
    # 1. 建目錄結構
    mkdir -p "$DIR"/{memories,sessions,logs,cron,skins,workspace,plans,cache,checkpoints,scripts,auth,browser_recordings,pastes,sandboxes,images,webui_state,.claude}
    
    # 2. config.yaml — 複製
    cp "$MASTER/config.yaml" "$DIR/config.yaml"
    
    # 3. skills/ → symlink 指向 master
    ln -sfn "$MASTER/skills" "$DIR/skills"
    echo "  ✅ skills/ → symlink to master"
    
    # 4. wiki/ → symlink 指向 master
    ln -sfn "$MASTER/wiki" "$DIR/wiki"
    echo "  ✅ wiki/ → symlink to master"
    
    # 5. .env — 複製（paper 模式，暫無券商憑證）
    cp "$MASTER/.env" "$DIR/.env"
    
    # 6. instances/ — 各自獨立
    mkdir -p "$DIR/instances/$PROFILE_NAME/state"
    
    # 7. 複製共用檔案
    cp "$MASTER/CLAUDE.md" "$DIR/CLAUDE.md" 2>/dev/null || true
    cp "$MASTER/GEMINI.md" "$DIR/GEMINI.md" 2>/dev/null || true
    cp "$MASTER/.gitignore" "$DIR/.gitignore" 2>/dev/null || true
    
    # 8. 獨立 DB
    touch "$DIR/state.db"
    
    echo "  ✅ $AGENT_NAME 目錄結構完成"
}

create_profile "etf_wife" "ETF_Wife" "太太的專屬理財助理" "太太"
create_profile "etf_son" "ETF_Son" "少爺的專屬理財助理" "少爺"
create_profile "etf_daughter" "ETF_Daughter" "千金的專屬理財助理" "千金"

echo ""
echo "🎉 3 個家人 profile 目錄建立完成！"
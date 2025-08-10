#!/bin/bash

# Reachy Mini 项目备份脚本
# 用于在网络问题时保存项目状态

echo "=== Reachy Mini 项目备份脚本 ==="
echo "开始时间: $(date)"

# 创建备份目录
BACKUP_DIR="$HOME/ReachyMini_Backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "备份目录: $BACKUP_DIR"

# 复制整个项目
echo "正在复制项目文件..."
cp -r /Users/lidejie/project/ReachyMini/* "$BACKUP_DIR/"
cp -r /Users/lidejie/project/ReachyMini/.* "$BACKUP_DIR/" 2>/dev/null || true

# 创建 Git 状态报告
echo "正在生成 Git 状态报告..."
cd /Users/lidejie/project/ReachyMini
git status > "$BACKUP_DIR/git_status.txt"
git log --oneline -10 > "$BACKUP_DIR/git_log.txt"
git diff --cached > "$BACKUP_DIR/git_staged_changes.txt" 2>/dev/null || true
git diff > "$BACKUP_DIR/git_unstaged_changes.txt" 2>/dev/null || true

# 创建项目信息文件
cat > "$BACKUP_DIR/backup_info.txt" << EOF
=== Reachy Mini 项目备份信息 ===
备份时间: $(date)
项目路径: /Users/lidejie/project/ReachyMini
GitHub 仓库: https://github.com/lidejieZQ/ReachyMini

=== 项目状态 ===
$(git status)

=== 最近提交 ===
$(git log --oneline -5)

=== 网络状态 ===
由于网络连接问题，无法推送到 GitHub
本地提交已保存，待网络恢复后可重新推送

=== 备份内容 ===
- 完整项目源代码
- 所有配置文件
- 文档和说明
- Git 历史记录
- 依赖配置文件
EOF

# 压缩备份
echo "正在压缩备份..."
cd "$HOME"
tar -czf "${BACKUP_DIR}.tar.gz" "$(basename $BACKUP_DIR)"

echo "备份完成!"
echo "备份文件: ${BACKUP_DIR}.tar.gz"
echo "备份目录: $BACKUP_DIR"
echo "结束时间: $(date)"

# 显示备份大小
echo "备份大小: $(du -sh ${BACKUP_DIR}.tar.gz | cut -f1)"
echo "目录大小: $(du -sh $BACKUP_DIR | cut -f1)"

echo ""
echo "=== 恢复说明 ==="
echo "1. 解压备份文件: tar -xzf ${BACKUP_DIR}.tar.gz"
echo "2. 进入项目目录: cd $(basename $BACKUP_DIR)"
echo "3. 检查 Git 状态: git status"
echo "4. 网络恢复后推送: git push origin master"
echo ""
echo "备份脚本执行完成!"
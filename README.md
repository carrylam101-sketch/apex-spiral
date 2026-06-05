# apex-spiral

> 一句话描述

## 项目简介

[链接](URL) — 详细说明项目是什么、解决什么问题

**核心功能**：
- 功能 1
- 功能 2
- 功能 3

## 备份内容清单

| 路径 | 大小 | 说明 |
|---|---|---|
| `src/` | X MB | 主代码 |
| `docs/` | X MB | 文档 |
| **合计** | **X MB** |  |

**已排除**（README 必读）：
- `*.dmg` / `*.exe` — 安装包在 GitHub Releases 单独发布
- `__pycache__/` — Python 字节码
- `*.env` — 敏感配置

## 还原到服务器

```bash
# 1. 克隆
git clone https://github.com/carrylam101-sketch/apex-spiral.git /tmp/restore
cd /tmp/restore

# 2. 复制到生产路径
rsync -a --exclude='.git' ./ /home/ubuntu/<生产路径>/

# 3. 重载服务（如适用）
sudo systemctl reload nginx
# 或
pm2 reload all

# 4. 验证
curl -I https://your-domain.com/
```

## 自动备份

每周一 03:00 由 `~/.hermes/scripts/backup/sync_to_github.sh` 自动跑增量备份。

## 技术栈

- 后端：xxx
- 前端：xxx
- 数据库：xxx
- 部署：xxx

## 联系方式

- 网站：URL
- 邮箱：xxx@example.com

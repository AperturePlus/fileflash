#!/bin/bash
# FileFlash 一键部署脚本
# 用法: 将整个项目上传到服务器后，在项目根目录执行 bash deploy.sh
#       bash deploy.sh --fresh   # 强制全量重建镜像（首次部署或大版本更新）

set -e

echo "========================================"
echo "  FileFlash 生产环境部署"
echo "========================================"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ---------- 1. 检查环境 ----------
echo -e "\n${YELLOW}[1/5] 检查环境...${NC}"

if ! command -v docker &>/dev/null; then
    echo -e "${RED}未安装 Docker，请先安装${NC}"
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo -e "${RED}需要 Docker Compose v2+${NC}"
    exit 1
fi

# ---------- 2. 生成密钥 ----------
echo -e "\n${YELLOW}[2/5] 生成安全密钥...${NC}"

JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(32))" 2>/dev/null)
ADMIN_PASSWORD=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(32))" 2>/dev/null)
DB_PASSWORD=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(16))" 2>/dev/null)
MINIO_PASSWORD=$(openssl rand -hex 16 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(16))" 2>/dev/null)

if [ -z "$JWT_SECRET" ] || [ -z "$ADMIN_PASSWORD" ] || [ -z "$DB_PASSWORD" ] || [ -z "$MINIO_PASSWORD" ]; then
    echo -e "${RED}无法生成密钥，请手动修改 docker/.env.production${NC}"
    exit 1
fi

# 替换 .env.production
sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" docker/.env.production
sed -i "s|^DEFAULT_ADMIN_PASSWORD=.*|DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD|" docker/.env.production
sed -i "s|^OBJECT_STORAGE_SECRET_KEY=.*|OBJECT_STORAGE_SECRET_KEY=$MINIO_PASSWORD|" docker/.env.production
sed -i "s|:psgl-ff-db@|:$DB_PASSWORD@|" docker/.env.production

# 替换 docker-compose.prod.yml
sed -i "s|POSTGRES_PASSWORD: psgl-ff-db|POSTGRES_PASSWORD: $DB_PASSWORD|" docker/docker-compose.prod.yml
sed -i "s|MINIO_ROOT_PASSWORD: minio-admin|MINIO_ROOT_PASSWORD: $MINIO_PASSWORD|" docker/docker-compose.prod.yml
sed -i "s|-password=psgl-ff-db|-password=$DB_PASSWORD|" docker/docker-compose.prod.yml

echo -e "${GREEN}JWT_SECRET_KEY 已生成${NC}"
echo -e "${GREEN}DEFAULT_ADMIN_PASSWORD 已生成${NC}"
echo -e "${GREEN}数据库密码 已生成${NC}"
echo -e "${GREEN}MinIO 密码 已生成${NC}"

# ---------- 3. 构建镜像 ----------
echo -e "\n${YELLOW}[3/5] 构建 Docker 镜像...${NC}"

BUILD_FLAGS=""
if [ "$1" = "--fresh" ]; then
    BUILD_FLAGS="--no-cache"
    echo -e "${YELLOW}  首次部署模式: 强制全量构建${NC}"
else
    echo "  增量构建 (使用层缓存，加 --fresh 可强制全量)"
fi

docker compose -f docker/docker-compose.prod.yml build $BUILD_FLAGS

echo -e "${GREEN}镜像构建完成${NC}"

# ---------- 4. 启动服务 ----------
echo -e "\n${YELLOW}[4/5] 启动服务...${NC}"

docker compose -f docker/docker-compose.prod.yml up -d

# ---------- 5. 等待就绪 ----------
echo -e "\n${YELLOW}[5/5] 等待服务就绪...${NC}"

echo -n "等待服务启动"
for i in $(seq 1 60); do
    if curl -s -o /dev/null http://localhost/health 2>/dev/null; then
        echo ""
        echo -e "${GREEN}服务已就绪${NC}"
        break
    fi
    echo -n "."
    sleep 3
done

echo ""
echo "========================================"
echo -e "${GREEN}  部署完成!${NC}"
echo "========================================"
echo ""
echo "管理员账号:"
echo "  用户名: administrator"
echo "  密码:   $ADMIN_PASSWORD"
echo ""
echo "数据库密码: $DB_PASSWORD"
echo "MinIO 密码:  $MINIO_PASSWORD"
echo ""
echo "访问 http://$(hostname -I | awk '{print $1}')"
echo ""
echo "常用命令:"
echo "  docker compose -f docker/docker-compose.prod.yml logs -f   # 查看日志"
echo "  docker compose -f docker/docker-compose.prod.yml down       # 停止"
echo "  docker compose -f docker/docker-compose.prod.yml restart    # 重启"
echo "  docker compose -f docker/docker-compose.prod.yml ps         # 状态"
echo ""
echo "如需开启 AI Agent:"
echo "  1. 修改 docker/.env.production 中 AGENT_ENABLED=true"
echo "  2. 配置 AGENT_LLM_BASE_URL 和 AGENT_LLM_API_KEY"
echo "  3. docker compose -f docker/docker-compose.prod.yml --profile agent up -d"

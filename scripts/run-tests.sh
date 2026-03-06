#!/bin/bash
# 测试运行脚本

set -e

echo "🧪 Feishu Organization Sync Service 测试"
echo "=========================================="

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  建议激活虚拟环境: source venv/bin/activate"
fi

# 安装测试依赖
echo "📦 安装依赖..."
pip install -q -r requirements.txt

# 运行单元测试
echo ""
echo "🧪 运行单元测试..."
pytest tests/unit -v --tb=short -m unit

# 生成覆盖率报告（可选）
if [ "$1" == "--coverage" ]; then
    echo ""
    echo "📊 生成覆盖率报告..."
    pytest tests/unit --cov=src --cov-report=html --cov-report=term
fi

# 运行集成测试（如果需要）
if [ "$1" == "--integration" ]; then
    echo ""
    echo "🔗 运行集成测试..."
    echo "请确保服务已启动: docker-compose up -d"
    pytest tests/integration -v -m integration
fi

echo ""
echo "✅ 测试完成!"

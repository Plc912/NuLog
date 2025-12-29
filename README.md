# NuLog 日志解析项目开发文档

MCP封住哪个作者：Plccc

github：https://github.com/Plc912/NuLog.git

邮箱：352236586@qq.com

## 目录

- [项目概述](#项目概述)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [安装说明](#安装说明)
- [快速开始](#快速开始)
- [MCP 服务器使用](#mcp-服务器使用)
- [API 文档](#api-文档)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

## 项目概述

NuLog 是一个基于自监督学习的日志解析工具，使用 Transformer 架构将半结构化日志消息解析为结构化模板。项目已封装为 MCP (Model Context Protocol) 服务器，可通过标准化的接口进行日志解析。

### 主要特性

- **自监督学习**：使用掩码语言模型 (MLM) 进行日志解析
- **多格式支持**：支持多种日志格式（BGL、HDFS、Apache、OpenStack 等）
- **MCP 服务器**：提供标准化的工具接口
- **CPU/GPU 支持**：自动检测并使用可用的计算设备

### 技术栈

- Python 3.11+
- PyTorch
- FastMCP
- NumPy, Pandas
- Keras Preprocessing

## 项目结构

```
nulog-master/
├── NuLog.py              # 核心日志解析器实现
├── mcp_server.py         # MCP 服务器实现
├── benchmark.py          # 基准测试脚本
├── demo.py               # 演示脚本
├── __init__.py           # 包初始化文件
├── requirements.txt      # 基础依赖（NumPy 1.x 兼容）
├── requirements_mcp.txt  # MCP 服务器依赖
├── README.md             # 项目说明
└── DEVELOPMENT.md        # 本开发文档
```

### 核心模块说明

- **NuLog.py**: 包含 `LogParser` 类，实现日志解析的核心逻辑
- **mcp_server.py**: 实现 MCP 服务器，提供 4 个工具函数
- **benchmark.py**: 基准测试脚本，测试多种日志格式的解析效果
- **demo.py**: 简单的使用示例

## 环境要求

### Python 版本

- Python 3.11 或更高版本（推荐 3.11.13）

### 系统要求

- Windows / Linux / macOS
- 至少 4GB RAM（推荐 8GB+）
- 可选：CUDA 支持的 GPU（用于加速训练）

### 依赖版本要求

**重要**: 由于 `keras_preprocessing` 的兼容性问题，必须使用 NumPy 1.x 版本：

- NumPy: < 2.0 (推荐 1.26.4)
- Pandas: < 2.2 (推荐 2.1.4)
- PyTorch: >= 1.3.1
- FastMCP: 最新版本

## 安装说明

### 1. 克隆项目（如果需要）

```bash
git clone <repository-url>
cd nulog-master
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 conda
conda create -n nulog python=3.11
conda activate nulog

# 或使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

#### 基础使用（命令行工具）

```bash
pip install -r requirements.txt
```

#### MCP 服务器

```bash
pip install -r requirements_mcp.txt
```

**注意**: `requirements_mcp.txt` 已包含所有必要的依赖，包括基础依赖。

### 4. 验证安装

```bash
python -c "from NuLog import LogParser; print('安装成功')"
```

## 快速开始

### 1. 命令行使用

#### 基本示例

编辑 `demo.py` 中的参数，然后运行：

```bash
python demo.py
```

#### 运行基准测试

```bash
python benchmark.py
```

**注意**: 基准测试需要相应的数据文件，请确保数据文件路径正确。

### 2. Python API 使用

```python
from NuLog import LogParser

# 初始化解析器
parser = LogParser(
    indir="path/to/log/directory",      # 输入目录
    outdir="path/to/output/directory",  # 输出目录
    filters="([ |:|\(|\)|=|,])",       # 正则表达式过滤器
    k=50,                                # top-k 参数
    log_format="<Date> <Time> <Level> <Content>"  # 日志格式
)

# 解析日志
parser.parse(
    log_file="log_file.log",  # 日志文件名
    nr_epochs=5,              # 训练轮数
    num_samples=0             # 采样数量（0=全部）
)
```

### 3. 日志格式说明

日志格式使用占位符定义，例如：

- `<Date>`: 日期字段
- `<Time>`: 时间字段
- `<Level>`: 日志级别
- `<Content>`: 日志内容

示例格式：

```
<Date> <Time> <Pid> <Level> <Component>: <Content>
```

## MCP 服务器使用

### 启动服务器

```bash
python mcp_server.py
```

服务器将在 `127.0.0.1:4005` 上启动，使用 SSE (Server-Sent Events) 传输。

### 配置 MCP 客户端

在 MCP 客户端配置文件中添加：

```json
{
  "mcpServers": {
    "nulog": {
      "command": "python",
      "args": ["path/to/mcp_server.py"],
      "transport": "sse",
      "url": "http://127.0.0.1:4005"
    }
  }
}
```

## API 文档

### MCP 工具列表

#### 1. parse_log

解析日志内容字符串。

**参数**:

- `log_content` (str): 日志内容字符串（多行文本）
- `log_format` (str): 日志格式，例如: `"<Date> <Time> <Pid> <Level> <Component>: <Content>"`
- `filters` (str, 可选): 正则表达式过滤器，默认: `"([ |:|\(|\)|=|,])|(core.)|(\.{2,})"`
- `k` (int, 可选): top-k 参数，默认: 50
- `nr_epochs` (int, 可选): 训练轮数，默认: 3
- `num_samples` (int, 可选): 采样数量（0=全部），默认: 0
- `batch_size` (int, 可选): 批次大小，默认: 5
- `pad_len` (int, 可选): 序列填充长度，默认: 150
- `limit` (int, 可选): 返回结果的最大数量，默认: 100

**返回**:

```json
{
  "status": "success",
  "templates": [
    {
      "EventId": "...",
      "EventTemplate": "..."
    }
  ],
  "count": 100,
  "returned_count": 100
}
```

**示例**:

```python
result = parse_log(
    log_content="2024-01-01 10:00:00 INFO Component: Log message",
    log_format="<Date> <Time> <Level> <Component>: <Content>",
    k=50,
    nr_epochs=3
)
```

#### 2. parse_log_file

解析磁盘上的日志文件。

**参数**:

- `file_path` (str): 日志文件的路径
- `log_format` (str): 日志格式
- `filters` (str, 可选): 正则表达式过滤器
- `k` (int, 可选): top-k 参数，默认: 50
- `nr_epochs` (int, 可选): 训练轮数，默认: 3
- `num_samples` (int, 可选): 采样数量，默认: 0
- `batch_size` (int, 可选): 批次大小，默认: 5
- `pad_len` (int, 可选): 序列填充长度，默认: 150
- `output_dir` (str, 可选): 输出目录（None=临时目录）
- `limit` (int, 可选): 返回结果的最大数量，默认: 100

**返回**:

```json
{
  "status": "success",
  "output_dir": "/path/to/output",
  "templates": [...],
  "count": 100,
  "returned_count": 100
}
```

**示例**:

```python
result = parse_log_file(
    file_path="/path/to/logfile.log",
    log_format="<Date> <Time> <Level> <Content>",
    output_dir="/path/to/output"
)
```

#### 3. benchmark_dataset

运行基准测试。

**参数**:

- `dataset_name` (str): 数据集名称（BGL, HDFS, Android, OpenStack, Apache, HPC, Windows, HealthApp, Mac, Spark）
- `input_dir` (str): 输入目录路径
- `output_dir` (str, 可选): 输出目录路径（None=临时目录）

**返回**:

```json
{
  "status": "success",
  "dataset": "HDFS",
  "output_dir": "/path/to/output",
  "parsed_result_file": "/path/to/output/HDFS_2k.log_structured.csv",
  "accuracy": 0.9965,
  "f1_score": null,
  "note": "..."
}
```

**示例**:

```python
result = benchmark_dataset(
    dataset_name="HDFS",
    input_dir="/path/to/data/loghub_2k"
)
```

#### 4. get_supported_formats

获取支持的日志格式列表。

**参数**: 无

**返回**:

```json
{
  "status": "success",
  "supported_datasets": ["BGL", "HDFS", "Android", ...],
  "formats": {
    "BGL": {
      "log_format": "...",
      "filters": "...",
      "k": 50,
      "nr_epochs": 3,
      "num_samples": 0
    },
    ...
  }
}
```

**示例**:

```python
formats = get_supported_formats()
print(formats["supported_datasets"])
```

### LogParser 类 API

#### 初始化

```python
parser = LogParser(
    indir: str,      # 输入目录
    outdir: str,     # 输出目录
    filters: str,    # 正则表达式过滤器
    k: int,          # top-k 参数
    log_format: str  # 日志格式
)
```

#### parse 方法

```python
parser.parse(
    logName: str,           # 日志文件名
    batch_size: int = 5,    # 批次大小
    mask_percentage: float = 1.0,  # 掩码比例
    pad_len: int = 150,     # 序列填充长度
    N: int = 1,             # Transformer 层数
    d_model: int = 256,     # 模型维度
    dropout: float = 0.1,   # Dropout 率
    lr: float = 0.001,      # 学习率
    betas: tuple = (0.9, 0.999),  # Adam 优化器参数
    weight_decay: float = 0.005,  # 权重衰减
    nr_epochs: int = 5,     # 训练轮数
    num_samples: int = 0,   # 采样数量
    step_size: int = 10     # 打印步长
)
```

## 开发指南

### 项目架构

1. **核心解析器** (`NuLog.py`)

   - 使用 Transformer 架构
   - 实现掩码语言模型 (MLM)
   - 支持 CPU 和 GPU 训练
2. **MCP 服务器** (`mcp_server.py`)

   - 基于 FastMCP 框架
   - 提供标准化的工具接口
   - 处理临时文件和错误
3. **工具函数**

   - `parse_log`: 解析字符串格式的日志
   - `parse_log_file`: 解析文件格式的日志
   - `benchmark_dataset`: 运行基准测试
   - `get_supported_formats`: 获取支持的格式

### 添加新的日志格式

1. 在 `BENCHMARK_SETTINGS` 中添加新配置：

```python
"NewFormat": {
    "log_file": "NewFormat/NewFormat_2k.log",
    "log_format": "<Date> <Time> <Content>",
    "filters": "([ ])",
    "k": 50,
    "nr_epochs": 5,
    "num_samples": 0,
}
```

2. 测试新格式：

```python
result = benchmark_dataset(
    dataset_name="NewFormat",
    input_dir="/path/to/data"
)
```

### 自定义过滤器

过滤器是正则表达式，用于 tokenization。常见模式：

- `([ ])`: 按空格分割
- `([ |:|\(|\)|=|,])`: 按多种分隔符分割
- `(\s+blk_)|(:)|(\s)`: 特定的分割规则（如 HDFS）

### 调试技巧

1. **启用详细输出**: 修改 `step_size` 参数以更频繁地打印训练信息
2. **减少训练轮数**: 开发时使用较小的 `nr_epochs` 值
3. **使用采样**: 设置 `num_samples` 以加快开发迭代
4. **检查临时文件**: MCP 工具会保留输出目录，可检查中间结果

### 性能优化

1. **GPU 加速**: 确保安装了 CUDA 版本的 PyTorch
2. **批次大小**: 根据内存调整 `batch_size`
3. **采样**: 对于大数据集，使用 `num_samples` 进行采样训练
4. **填充长度**: 根据日志平均长度调整 `pad_len`

## 常见问题

### 1. NumPy 版本兼容性问题

**问题**: `AttributeError: np.unicode_ was removed in the NumPy 2.0 release`

**解决方案**: 使用 NumPy 1.x 版本

```bash
pip install "numpy<2.0"
```

### 2. 导入错误

**问题**: `Import "logparser.NuLog" could not be resolved`

**解决方案**: 项目结构已更改，使用直接导入

```python
from NuLog import LogParser  # 正确
# from logparser.NuLog import LogParser  # 错误
```

### 3. 内存不足

**解决方案**:

- 减少 `batch_size`
- 减少 `pad_len`
- 使用 `num_samples` 进行采样
- 使用 GPU 加速

### 4. 训练时间过长

**解决方案**:

- 减少 `nr_epochs`
- 使用 `num_samples` 进行采样
- 使用 GPU 加速
- 减少 `pad_len`

### 5. MCP 服务器无法启动

**检查清单**:

- 确保已安装所有依赖: `pip install -r requirements_mcp.txt`
- 检查端口 4005 是否被占用
- 检查 Python 版本是否为 3.11+

### 6. 解析结果为空

**可能原因**:

- 日志格式定义不正确
- 过滤器正则表达式不匹配
- 日志文件编码问题（确保使用 UTF-8）

## 贡献指南

### 代码规范

- 使用 Python 3.11+ 语法
- 遵循 PEP 8 代码风格
- 添加适当的文档字符串
- 使用类型提示（Type Hints）

### 提交变更

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

本项目遵循原 NuLog 项目的许可证。

## 参考资源

- [NuLog 原始项目](https://github.com/nulog/nulog)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [PyTorch 文档](https://pytorch.org/docs/)
- [MCP 协议规范](https://modelcontextprotocol.io/)

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

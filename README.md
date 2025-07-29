# Easy SQL Show - CSV数据可视化工具

一个基于Flask的Web应用，能够自动将CSV文件转换为SQLite数据库，并提供实时数据可视化展示。

## 🚀 主要功能

### 1. 智能CSV处理
- **自动结构分析**：分析CSV文件结构并推断数据类型
- **动态表生成**：根据CSV内容自动生成SQLite表结构
- **数据导入**：将CSV数据自动导入到数据库中

### 2. 实时数据更新
- **文件变化检测**：使用MD5哈希值检测CSV文件变化
- **自动更新**：当CSV文件发生变化时自动更新数据库
- **性能优化**：避免不必要的重复处理

### 3. Web界面展示
- **数据表格**：以HTML表格形式展示数据库内容
- **实时刷新**：支持手动刷新数据
- **响应式设计**：适配不同屏幕尺寸

## 📁 项目结构

```
easy_sqlshow/
├── app.py                 # 主程序文件（包含所有功能）
├── static/
│   ├── data.csv          # CSV数据文件
│   ├── summary.db        # SQLite数据库文件
│   ├── summary.db.hash   # 文件变化检测哈希值
│   ├── style.css         # 样式文件
│   └── logo.png          # 网站Logo
├── templates/
│   └── index.html        # 网页模板
└── README.md             # 项目说明文档
```

## 🛠️ 安装和运行

### 环境要求
- Python 3.6+
- Flask

### 安装依赖
```bash
pip install flask
```

### 运行方式

#### 1. Web模式（推荐）
```bash
python app.py
```
- 启动Flask Web服务器
- 访问 http://127.0.0.1:5000 查看数据
- 自动检测CSV文件变化并更新

#### 2. 脚本模式
```bash
# 使用默认CSV文件
python app.py

# 指定CSV文件
python app.py ./static/your_file.csv

# 指定CSV文件和表名
python app.py ./static/your_file.csv YourTableName

# 指定CSV文件、表名和数据库路径
python app.py ./static/your_file.csv YourTableName ./static/your_db.db
```

## 📊 CSV文件格式

### 支持的列结构
- **固定列**：`dataset`, `version`, `metric`, `mode`
- **动态列**：自动检测并添加额外的数据列
- **数据类型**：自动推断TEXT、INTEGER、DECIMAL等类型

### 示例CSV格式
```csv
dataset,version,metric,mode,qwen2.5-1.5b-instruct-hf,test
demo100afqmc-dev,6507d7,accuracy,ppl,0,test
demo100math,11c4b5,accuracy,gen,42,test
```

## 🔄 数据更新机制

### 自动更新
- 程序会自动检测CSV文件的变化
- 当文件内容发生变化时，自动重新处理数据
- 使用MD5哈希值进行高效的文件变化检测

### 手动刷新
- 访问 http://127.0.0.1:5000/refresh 强制更新数据
- 忽略文件变化检测，强制重新处理CSV文件

## 🎯 使用场景

### 1. 数据分析展示
- 将分析结果CSV文件转换为可视化表格
- 实时更新分析结果

### 2. 模型评估结果展示
- 展示机器学习模型的评估指标
- 支持多模型对比数据

### 3. 数据监控面板
- 实时监控数据变化
- 提供直观的数据展示界面

## ⚙️ 配置说明

### 文件路径配置
- **CSV文件**：默认 `./static/data.csv`
- **数据库文件**：默认 `./static/summary.db`
- **表名**：默认 `ModelEvaluation`

### 数据类型推断
- **数值型**：自动识别为DECIMAL(10, 4)
- **文本型**：自动识别为TEXT
- **日期型**：自动识别为DATETIME

## 🔧 高级功能

### 1. 列名清理
- 自动清理特殊字符
- 转换为SQL兼容的列名
- 处理连字符等特殊符号

### 2. 空值处理
- 智能处理CSV中的空值
- 自动转换为NULL或默认值

### 3. 错误处理
- 完善的异常处理机制
- 详细的错误信息输出

## 📝 开发说明

### 核心函数
- `process_csv_to_database()`: 处理CSV到数据库的完整流程
- `generate_sql_table()`: 生成SQL表结构
- `import_csv_to_db()`: 导入CSV数据
- `read_sqlite_data()`: 读取数据库数据

### 扩展性
- 支持自定义CSV文件格式
- 可扩展的数据类型推断
- 灵活的数据库结构生成

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目采用MIT许可证。

---

**注意**：这是一个开发服务器，不建议在生产环境中使用。生产环境请使用专业的WSGI服务器。 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV到SQL表结构生成器 + 数据库创建 + 数据导入 + Web展示 - 合并版本
根据CSV文件动态生成SQL表结构，创建数据库，导入数据，并提供Web界面展示
"""

import csv
import re
import os
import sys
import sqlite3
import hashlib
from typing import List, Dict
from flask import Flask, render_template

app = Flask(__name__)


def clean_column_name(column_name: str, preserve_chinese: bool = False) -> str:
    """
    清理列名，使其符合SQL标识符规范
    
    Args:
        column_name: 原始列名
        preserve_chinese: 是否保留中文字符
        
    Returns:
        清理后的列名
    """
    if preserve_chinese:
        # 保留中文字符，只移除特殊符号
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '_', column_name)
    else:
        # 移除特殊字符，只保留字母、数字和下划线
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', column_name)
    
    # 确保不以数字开头
    if cleaned and cleaned[0].isdigit():
        cleaned = 'col_' + cleaned
    
    if not preserve_chinese:
        # 转换为小写（仅当不保留中文时）
        cleaned = cleaned.lower()
    
    # 移除连续的下划线
    cleaned = re.sub(r'_+', '_', cleaned)
    # 移除开头和结尾的下划线
    cleaned = cleaned.strip('_')
    return cleaned


def infer_data_type(sample_values: List[str]) -> str:
    """
    根据样本值推断数据类型
    
    Args:
        sample_values: 样本值列表
        
    Returns:
        SQL数据类型
    """
    if not sample_values:
        return 'TEXT'
    
    # 检查是否为数字
    numeric_count = 0
    decimal_count = 0
    scientific_count = 0
    
    for value in sample_values:
        if value.strip():
            try:
                # 检查是否包含科学计数法
                if 'E' in value.upper() or 'e' in value:
                    float_val = float(value)
                    numeric_count += 1
                    scientific_count += 1
                    # 检查数值是否过大
                    if abs(float_val) > 1e308 or (abs(float_val) < 1e-308 and float_val != 0):
                        # 如果数值过大，直接返回TEXT类型
                        return 'TEXT'
                else:
                    float_val = float(value)
                    numeric_count += 1
                    if '.' in value:
                        decimal_count += 1
            except (ValueError, OverflowError):
                pass
    
    # 如果大部分是数字
    if numeric_count > len(sample_values) * 0.8:
        if scientific_count > 0:
            # 包含科学计数法，使用TEXT类型以保持精度
            return 'TEXT'
        elif decimal_count > 0:
            return 'DECIMAL(10, 4)'
        else:
            return 'INTEGER'
    
    # 检查是否为日期时间
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2}/\d{2}/\d{4}',
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    ]
    
    for pattern in date_patterns:
        if all(re.match(pattern, value) for value in sample_values if value.strip()):
            return 'DATETIME'
    
    # 默认返回TEXT
    return 'TEXT'


def analyze_csv_structure(csv_file_path: str, sample_rows: int = 10) -> List[Dict]:
    """
    分析CSV文件结构
    
    Args:
        csv_file_path: CSV文件路径
        sample_rows: 用于分析数据类型的样本行数
        
    Returns:
        列信息列表
    """
    columns_info = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # 读取表头
        headers = next(reader)
        
        # 收集样本数据
        sample_data = []
        for i, row in enumerate(reader):
            if i >= sample_rows:
                break
            sample_data.append(row)
        
        # 分析每一列
        for col_index, header in enumerate(headers):
            # 清理列名 - 第5列之后保留中文字符
            if col_index >= 5:
                clean_name = clean_column_name(header, preserve_chinese=True)
            else:
                clean_name = clean_column_name(header, preserve_chinese=False)
            
            # 收集该列的样本值
            col_samples = []
            for row in sample_data:
                if col_index < len(row):
                    col_samples.append(row[col_index])
            
            # 推断数据类型
            data_type = infer_data_type(col_samples)
            
            columns_info.append({
                'original_name': header,
                'clean_name': clean_name,
                'data_type': data_type,
                'index': col_index
            })
    
    return columns_info


def generate_sql_table(csv_file_path: str, table_name: str = "ModelEvaluation", sample_rows: int = 10) -> str:
    """
    根据CSV文件生成SQL表结构，保持与summary.sql相同的命名规范
    
    Args:
        csv_file_path: CSV文件路径
        table_name: 表名（默认为ModelEvaluation）
        sample_rows: 用于分析数据类型的样本行数
        
    Returns:
        SQL建表语句
    """
    # 分析CSV结构
    columns_info = analyze_csv_structure(csv_file_path, sample_rows)
    
    # 生成SQL语句
    sql_lines = []
    sql_lines.append("-- 创建模型评估结果表")
    sql_lines.append(f"CREATE TABLE IF NOT EXISTS {table_name} (")
    
    # 添加固定列定义（使用中文列名）
    column_definitions = [
        "    序号 INTEGER PRIMARY KEY AUTOINCREMENT",
        "    数据集 TEXT NOT NULL",
        "    版本 TEXT NOT NULL", 
        "    评估指标 TEXT NOT NULL",
        "    参数 TEXT NOT NULL",
        "    模式 TEXT NOT NULL",
    ]
    
    # 根据CSV列数动态添加额外的列
    if len(columns_info) > 5:  # 如果CSV有超过6列（前6列对应固定列）
        for i in range(5, len(columns_info)):
            col_info = columns_info[i]
            # 根据推断的数据类型设置列定义
            # 对于中文列名，使用双引号包围
            if col_info['data_type'] == 'TEXT':
                col_def = f'    "{col_info["clean_name"]}" TEXT'
            elif col_info['data_type'] == 'INTEGER':
                col_def = f'    "{col_info["clean_name"]}" INTEGER'
            else:
                # 默认使用DECIMAL类型，允许NULL值
                col_def = f'    "{col_info["clean_name"]}" DECIMAL(10, 4)'
            column_definitions.append(col_def)
    
    sql_lines.append(",\n".join(column_definitions))
    sql_lines.append(");")
    
    return "\n".join(sql_lines)


def create_database(sql_content: str, db_path: str = "./static/summary.db"):
    """
    创建数据库并执行SQL脚本
    
    Args:
        sql_content: SQL脚本内容
        db_path: 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 执行SQL脚本创建表
    cursor.executescript(sql_content)

    conn.commit()
    conn.close()


def import_csv_to_db(csv_file_path: str, db_path: str = "./static/summary.db"):
    """
    将CSV数据导入到数据库
    
    Args:
        csv_file_path: CSV文件路径
        db_path: 数据库文件路径
    """
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 清空现有数据（可选）
    cursor.execute("DELETE FROM ModelEvaluation")
    
    # 读取CSV文件
    with open(csv_file_path, "r", encoding="utf-8") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        
        # 获取CSV文件的列名
        original_fieldnames = csv_reader.fieldnames
        
        # 清理列名，使其与数据库表结构匹配
        fieldnames = []
        for i, field in enumerate(original_fieldnames):
            if i == 0:  # dataset -> 数据集
                fieldnames.append('数据集')
            elif i == 1:  # version -> 版本
                fieldnames.append('版本')
            elif i == 2:  # metric -> 评估指标
                fieldnames.append('评估指标')
            elif i == 3:  # parameter -> 参数
                fieldnames.append('参数')
            elif i == 4:  # mode -> 模式
                fieldnames.append('模式')
            else:
                # 其他列使用清理后的列名，保留中文字符
                fieldnames.append(clean_column_name(field, preserve_chinese=True))
        
        # 动态生成插入语句
        # 对于中文列名，使用双引号包围
        quoted_columns = []
        for field in fieldnames:
            if any('\u4e00' <= char <= '\u9fff' for char in field):  # 检查是否包含中文字符
                quoted_columns.append(f'"{field}"')
            else:
                quoted_columns.append(field)
        
        columns = ', '.join(quoted_columns)
        placeholders = ', '.join(['?' for _ in fieldnames])
        insert_sql = f"""
        INSERT INTO ModelEvaluation 
        ({columns}) 
        VALUES ({placeholders})
        """
        
        # 插入数据
        for row in csv_reader:
            # 动态构建值列表，处理数值类型转换
            values = []
            for i, field in enumerate(original_fieldnames):
                value = row[field]
                # 处理空值
                if not value or not value.strip():
                    values.append(None)
                else:
                    # 前5列保持为字符串
                    if i < 5:
                        values.append(value)
                    else:
                        # 第6列开始尝试转换为数值类型
                        try:
                            # 处理科学计数法格式
                            if 'E' in value.upper() or 'e' in value:
                                # 科学计数法格式，需要特殊处理
                                float_val = float(value)
                                # 检查数值是否过大或过小，避免SQLite精度问题
                                if abs(float_val) > 1e308 or (abs(float_val) < 1e-308 and float_val != 0):
                                    # 数值超出SQLite的REAL类型范围，存储为字符串
                                    values.append(value)
                                else:
                                    values.append(float_val)
                            else:
                                # 普通数值格式
                                float_val = float(value)
                                values.append(float_val)
                        except (ValueError, OverflowError):
                            # 如果转换失败，保持原始字符串值
                            values.append(value)
            
            cursor.execute(insert_sql, values)
    
    # 提交事务
    conn.commit()
    
    # 获取插入的记录数
    cursor.execute("SELECT COUNT(*) FROM ModelEvaluation")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


def get_file_hash(file_path: str) -> str:
    """
    获取文件的MD5哈希值，用于检测文件变化
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件的MD5哈希值
    """
    if not os.path.exists(file_path):
        return ""
    
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def process_csv_to_database(csv_file_path: str = "./static/data.csv", 
                           table_name: str = "ModelEvaluation", 
                           db_path: str = "./static/summary.db",
                           force_update: bool = False):
    """
    处理CSV到数据库的完整流程
    
    Args:
        csv_file_path: CSV文件路径
        table_name: 表名
        db_path: 数据库文件路径
        force_update: 是否强制更新（忽略文件变化检测）
        
    Returns:
        导入的记录数
    """
    try:
        # 检查CSV文件是否存在
        if not os.path.exists(csv_file_path):
            print(f"错误: 找不到CSV文件 {csv_file_path}")
            return 0
        
        # 检查是否需要更新（通过文件哈希值比较）
        csv_hash_file = db_path + ".hash"
        current_hash = get_file_hash(csv_file_path)
        
        # 读取之前的哈希值
        previous_hash = ""
        if os.path.exists(csv_hash_file):
            with open(csv_hash_file, 'r') as f:
                previous_hash = f.read().strip()
        
        # 如果文件没有变化且不是强制更新，则跳过处理
        if not force_update and current_hash == previous_hash and os.path.exists(db_path):
            print("CSV文件未发生变化，跳过数据库更新")
            return -1  # 返回-1表示没有更新
        
        print("检测到CSV文件变化，正在更新数据库...")
        
        # 检查并删除已存在的数据库文件
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"已删除现有数据库文件: {db_path}")
        
        # 步骤1: 生成SQL表结构
        sql_content = generate_sql_table(csv_file_path, table_name)
        
        # 步骤2: 创建数据库
        create_database(sql_content, db_path)
        
        # 步骤3: 导入CSV数据
        count = import_csv_to_db(csv_file_path, db_path)
        
        # 保存新的哈希值
        with open(csv_hash_file, 'w') as f:
            f.write(current_hash)
        
        # 输出结果
        print(f"成功处理CSV文件: {os.path.basename(csv_file_path)}")
        print(f"数据库文件: {db_path}")
        print(f"导入记录数: {count}")
        
        return count
        
    except FileNotFoundError:
        print(f"错误: 找不到CSV文件 {csv_file_path}")
        return 0
    except Exception as e:
        print(f"错误: {str(e)}")
        return 0


def render_table(data):
    """
    将数据渲染为HTML表格
    
    Args:
        data: 数据列表，第一行为列名
        
    Returns:
        HTML表格字符串
    """
    # 如果没有数据，返回空字符串
    if not data:
        return ''
    
    html = '<table><thead><tr>'
    # 渲染表头
    for col in data[0]:
        html += f'<th>{str(col)}</th>'
    html += '</tr></thead><tbody>'
    
    # 渲染每一行数据
    for row in data[1:]:
        html += '<tr>'
        for i, cell in enumerate(row):
            # 格式化数值显示
            if i > 5 and cell is not None:  # 第6列开始是数值列
                try:
                    # 尝试转换为浮点数并格式化
                    float_val = float(cell)
                    cell_str = str(cell)
                    # 检查小数位数
                    if '.' in cell_str:
                        decimal_places = len(cell_str.split('.')[1])
                        if decimal_places < 2:
                            # 小数位数不足两位，补到两位
                            formatted_cell = f"{float_val:.2f}"
                        else:
                            # 小数位数足够，保持原样
                            formatted_cell = cell_str
                    else:
                        # 整数，格式化为两位小数
                        formatted_cell = f"{float_val:.2f}"
                except (ValueError, TypeError):
                    formatted_cell = str(cell)
            else:
                formatted_cell = str(cell)
            
            html += f'<td>{formatted_cell}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


def read_sqlite_data(db_path):
    """
    读取SQLite数据库文件
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        数据列表，第一行为列名
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            return []
        
        # 获取第一个表的数据（如果有多个表，这里取第一个）
        table_name = tables[0][0]
        cursor.execute(f"SELECT * FROM {table_name}")
        
        # 获取列名
        columns = [description[0] for description in cursor.description]
        
        # 获取所有数据
        rows = cursor.fetchall()
        
        # 将列名作为第一行，数据作为后续行
        data = [columns] + list(rows)
        
        conn.close()
        return data
    except Exception as e:
        print(f"读取数据库时出错: {e}")
        return []


@app.route('/')
def index():
    """
    Web应用主页路由
    """
    table_html = ''
    # 拼接数据库文件的绝对路径
    db_path = os.path.join(app.root_path, 'static', 'summary.db')
    csv_file_path = os.path.join(app.root_path, 'static', 'data.csv')
    
    # 检查CSV文件是否存在并处理数据
    if os.path.exists(csv_file_path):
        # 处理CSV数据（会自动检测文件变化）
        result = process_csv_to_database(csv_file_path, "ModelEvaluation", db_path)
        if result > 0:
            print(f"数据库已更新，导入 {result} 条记录")
        elif result == -1:
            print("数据库无需更新")
        elif result == 0:
            # 如果处理失败，尝试强制更新
            print("尝试强制更新数据库...")
            result = process_csv_to_database(csv_file_path, "ModelEvaluation", db_path, force_update=True)
            if result > 0:
                print(f"强制更新成功，导入 {result} 条记录")
            else:
                print("强制更新失败")
    else:
        print(f"CSV文件不存在: {csv_file_path}")
    
    # 判断数据库文件是否存在
    if os.path.exists(db_path):
        # 获取分组统计数据
        grouped_data = get_grouped_statistics(db_path)
        # 渲染分组统计表格
        table_html = render_grouped_table(grouped_data)
    else:
        print(f"数据库文件不存在: {db_path}")
        table_html = "<p>数据库文件不存在</p>"
    
    # 渲染页面模板，并传递表格HTML
    return render_template('index.html', table=table_html)


def get_grouped_statistics(db_path):
    """
    获取按dataset分组并按metric统计的数据
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ModelEvaluation'")
        if not cursor.fetchone():
            print("错误: ModelEvaluation 表不存在")
            return []
        
        # 首先获取所有数值列名（除了前4列：dataset, version, metric, mode）
        try:
            cursor.execute("PRAGMA table_info(ModelEvaluation)")
            columns_info = cursor.fetchall()
            
            # 打印当前表结构，用于调试
            print("当前表结构:")
            for i, col_info in enumerate(columns_info):
                print(f"  列 {i}: {col_info[1]} ({col_info[2]})")
        except Exception as e:
            print(f"获取表结构时出错: {e}")
            return []
        
        # 获取数值列名（动态识别，跳过前5列）
        numeric_columns = []
        for i, col_info in enumerate(columns_info):
            if i >= 5:  # 跳过前5列，从第6列开始
                column_name = col_info[1]
                # 跳过模式列，它不应该是数值列
                if column_name != '模式':
                    # 处理列名中的特殊字符
                    safe_column_name = f'"{column_name}"'
                    numeric_columns.append((column_name, safe_column_name))
        
        print(f"识别到的数值列: {[col[0] for col in numeric_columns]}")
        
        if not numeric_columns:
            return []
        
        # 使用SQL实现双重分组和平均值计算
        sql_query = f"""
        WITH dataset_groups AS (
            SELECT 
                数据集,
                版本,
                评估指标,
                参数,
                模式,
                """ + ', '.join([f'"{col_name}"' for col_name, _ in numeric_columns]) + """,
                CASE 
                    WHEN INSTR(数据集, '_') > 0 AND INSTR(数据集, '-') > 0 THEN 
                        CASE 
                            WHEN INSTR(数据集, '_') < INSTR(数据集, '-') THEN SUBSTR(数据集, 1, INSTR(数据集, '_') - 1)
                            ELSE SUBSTR(数据集, 1, INSTR(数据集, '-') - 1)
                        END
                    WHEN INSTR(数据集, '_') > 0 THEN SUBSTR(数据集, 1, INSTR(数据集, '_') - 1)
                    WHEN INSTR(数据集, '-') > 0 THEN SUBSTR(数据集, 1, INSTR(数据集, '-') - 1)
                    ELSE 数据集 
                END as dataset_identifier,
                ROW_NUMBER() OVER (
                    PARTITION BY CASE 
                        WHEN INSTR(数据集, '_') > 0 AND INSTR(数据集, '-') > 0 THEN 
                            CASE 
                                WHEN INSTR(数据集, '_') < INSTR(数据集, '-') THEN SUBSTR(数据集, 1, INSTR(数据集, '_') - 1)
                                ELSE SUBSTR(数据集, 1, INSTR(数据集, '-') - 1)
                            END
                        WHEN INSTR(数据集, '_') > 0 THEN SUBSTR(数据集, 1, INSTR(数据集, '_') - 1)
                        WHEN INSTR(数据集, '-') > 0 THEN SUBSTR(数据集, 1, INSTR(数据集, '-') - 1)
                        ELSE 数据集 
                    END, 评估指标
                    ORDER BY 数据集, 版本, 评估指标
                ) as row_num
            FROM ModelEvaluation
        ),
        avg_values AS (
            SELECT 
                dataset_identifier,
                评估指标,
                """ + ', '.join([f'AVG("{col_name}") as avg_{col_name}' for col_name, _ in numeric_columns]) + """
            FROM dataset_groups
            GROUP BY dataset_identifier, 评估指标
        )
        SELECT 
            CASE WHEN d.row_num = 1 THEN d.dataset_identifier ELSE '' END as 数据集,
            d.版本,
            d.评估指标,
            d.参数,
            d.模式,
            """ + ', '.join([f'CASE WHEN d.row_num = 1 THEN a.avg_{col_name} ELSE NULL END as "{col_name}"' for col_name, _ in numeric_columns]) + """
        FROM dataset_groups d
        LEFT JOIN avg_values a ON d.dataset_identifier = a.dataset_identifier AND d.评估指标 = a.评估指标
        ORDER BY d.dataset_identifier, d.评估指标, d.row_num
        """
        
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # 获取列名
        column_names = [desc[0] for desc in cursor.description]
        
        conn.close()
        
        # 转换为字典列表
        data = []
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                row_dict[column_names[i]] = value
            data.append(row_dict)
        
        return data
        
    except Exception as e:
        print(f"获取分组统计时出错: {e}")
        import traceback
        traceback.print_exc()
        return []


def render_grouped_table(data):
    """
    渲染分组统计表格
    """
    if not data:
        return "<p>暂无数据</p>"
    
    html = '<div class="table-container">'
    html += '<table class="data-table">'
    
    # 表头
    html += '<thead><tr>'
    for key in data[0].keys():
        html += f'<th>{key}</th>'
    html += '</tr></thead>'
    
    # 表体
    html += '<tbody>'
    for row in data:
        html += '<tr>'
        for i, (key, value) in enumerate(row.items()):
            if i == 0:  # 第一列（数据集）
                # SQL已经处理了数据集名的显示，直接显示即可
                formatted_value = str(value) if value is not None else ''
                html += f'<td>{formatted_value}</td>'
            else:
                # 其他列正常显示
                if key not in ['数据集', '评估指标', '参数', '模式', '版本'] and value is not None:
                    # 格式化数值列，保留2位小数
                    try:
                        if isinstance(value, (int, float)):
                            formatted_value = f"{float(value):.2f}"
                        else:
                            formatted_value = f"{float(value):.2f}"
                    except (ValueError, TypeError):
                        formatted_value = str(value)
                else:
                    formatted_value = str(value) if value is not None else ''
                html += f'<td>{formatted_value}</td>'
        html += '</tr>'
    html += '</tbody>'
    
    html += '</table></div>'
    return html


@app.route('/refresh')
def refresh():
    """
    强制刷新路由 - 强制重新处理CSV数据
    """
    db_path = os.path.join(app.root_path, 'static', 'summary.db')
    csv_file_path = os.path.join(app.root_path, 'static', 'data.csv')
    
    if os.path.exists(csv_file_path):
        # 强制更新数据库
        result = process_csv_to_database(csv_file_path, "ModelEvaluation", db_path, force_update=True)
        if result > 0:
            return f"数据库已强制更新，导入 {result} 条记录"
        else:
            return "数据库更新失败"
    else:
        return "CSV文件不存在"


def main():
    """
    主函数 - 执行完整的CSV到数据库流程
    """
    # 默认文件路径
    csv_file_path = "./static/data.csv"
    table_name = "ModelEvaluation"
    db_path = "./static/summary.db"
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        csv_file_path = sys.argv[1]
    if len(sys.argv) > 2:
        table_name = sys.argv[2]
    if len(sys.argv) > 3:
        db_path = sys.argv[3]
    
    try:
        # 处理CSV到数据库
        process_csv_to_database(csv_file_path, table_name, db_path)
    finally:
        # 脚本结束时删除hash文件
        hash_file_path = db_path + ".hash"
        if os.path.exists(hash_file_path):
            os.remove(hash_file_path)
            print("已删除hash文件")


if __name__ == '__main__':
    # 如果作为脚本运行，执行数据处理
    if len(sys.argv) > 1:
        main()
    else:
        # 如果作为Web应用运行，启动Flask服务器
        print("启动Web服务器...")
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        except KeyboardInterrupt:
            print("\n程序正在退出...")
        finally:
            # 程序结束时删除hash文件
            hash_file_path = "./static/summary.db.hash"
            if os.path.exists(hash_file_path):
                os.remove(hash_file_path)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV文件新增随机数列程序 - 简化版
"""

import csv
import random
import sys

def add_random_column_simple(csv_file, new_column_name):
    """
    简化版：在CSV文件中新增一列随机数
    固定为最小值0，最大值100，两位小数
    """
    try:
        # 读取原文件
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            print("文件为空")
            return
        
        # 添加新列名
        rows[0].append(new_column_name)
        
        # 为每行添加随机数（整数和浮点数混合）
        for i in range(1, len(rows)):
            # 随机决定是整数还是浮点数
            if random.choice([True, False]):  # 50%概率生成整数
                random_val = random.randint(0, 100)
            else:  # 50%概率生成浮点数
                random_val = round(random.uniform(0.0, 100.0), 2)
            rows[i].append(random_val)
        
        # 写回文件
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        print(f"成功添加列 '{new_column_name}'，共 {len(rows)-1} 行数据")
        print("随机数范围：0-100，包含整数和浮点数")
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python add_column_simple.py <CSV文件> <新列名>")
        print("示例: python add_column_simple.py data.csv 随机分数")
        print("注意：随机数范围0-100，包含整数和浮点数")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    new_column_name = sys.argv[2]
    
    add_random_column_simple(csv_file, new_column_name) 
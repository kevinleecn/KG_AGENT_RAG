#!/usr/bin/env python3
"""
测试PDF解析性能
"""
import os
import sys
import time
from pathlib import Path

# 添加项目路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_pypdf2(file_path):
    """测试PyPDF2解析性能"""
    try:
        from PyPDF2 import PdfReader

        start_time = time.time()

        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            page_count = len(reader.pages)
            print(f"PyPDF2: 文件有 {page_count} 页")

            # 尝试提取前3页文本
            all_text = []
            for i, page in enumerate(reader.pages[:3]):
                try:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                        print(f"  第 {i+1} 页: {len(text)} 字符")
                    else:
                        print(f"  第 {i+1} 页: 无文本")
                except Exception as e:
                    print(f"  第 {i+1} 页错误: {e}")

            elapsed = time.time() - start_time
            print(f"PyPDF2解析时间: {elapsed:.2f} 秒")
            return True, elapsed, page_count

    except Exception as e:
        print(f"PyPDF2测试失败: {e}")
        return False, 0, 0

def test_pdfplumber(file_path):
    """测试pdfplumber解析性能"""
    try:
        import pdfplumber

        start_time = time.time()

        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            print(f"pdfplumber: 文件有 {page_count} 页")

            # 尝试提取前3页文本
            all_text = []
            for i, page in enumerate(pdf.pages[:3]):
                try:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                        print(f"  第 {i+1} 页: {len(text)} 字符")
                    else:
                        print(f"  第 {i+1} 页: 无文本")
                except Exception as e:
                    print(f"  第 {i+1} 页错误: {e}")

            elapsed = time.time() - start_time
            print(f"pdfplumber解析时间: {elapsed:.2f} 秒")
            return True, elapsed, page_count

    except Exception as e:
        print(f"pdfplumber测试失败: {e}")
        return False, 0, 0

def main():
    file_path = project_dir / "static" / "uploads" / "natron-ul-9540a-cell-report-revised-july-8-2020-final.pdf"

    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        return

    print(f"测试PDF文件: {file_path}")
    print(f"文件大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    print()

    print("=" * 60)
    print("测试PyPDF2...")
    print("-" * 60)
    pypdf2_success, pypdf2_time, pypdf2_pages = test_pypdf2(file_path)

    print()
    print("=" * 60)
    print("测试pdfplumber...")
    print("-" * 60)
    pdfplumber_success, pdfplumber_time, pdfplumber_pages = test_pdfplumber(file_path)

    print()
    print("=" * 60)
    print("性能总结:")
    print(f"PyPDF2: {'成功' if pypdf2_success else '失败'}, 时间: {pypdf2_time:.2f}秒, 页数: {pypdf2_pages}")
    print(f"pdfplumber: {'成功' if pdfplumber_success else '失败'}, 时间: {pdfplumber_time:.2f}秒, 页数: {pdfplumber_pages}")

    if pypdf2_success and pdfplumber_success:
        if pypdf2_time < pdfplumber_time:
            print("建议: 使用PyPDF2 (更快)")
        else:
            print("建议: 使用pdfplumber (更准确)")
    elif pypdf2_success:
        print("建议: 使用PyPDF2 (pdfplumber失败)")
    elif pdfplumber_success:
        print("建议: 使用pdfplumber (PyPDF2失败)")
    else:
        print("两个库都失败了")

if __name__ == "__main__":
    main()
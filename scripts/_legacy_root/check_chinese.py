"""检查DOCX文件的中文字符数量"""
import sys
from docx import Document

def count_chinese(text):
    """计算中文字符数量"""
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")

def check_docx_chinese(docx_path):
    """检查DOCX文件的中文字符数量"""
    try:
        doc = Document(docx_path)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        chinese_count = count_chinese(full_text)
        total_chars = len(full_text)
        print(f"文件: {docx_path}")
        print(f"总字符数: {total_chars}")
        print(f"中文字符数: {chinese_count}")
        if chinese_count < 100:
            print(f"中文字符不足: {chinese_count} < 100")
        else:
            print("中文字符数量充足")
        return chinese_count
    except Exception as e:
        print(f"检查失败: {e}")
        return 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_docx_chinese(sys.argv[1])
    else:
        print("使用方法: python check_chinese.py <docx文件路径>")
# utils/exporter.py
import json
import shutil
from pathlib import Path

def export_report(output_dir: str, annotated_pdf_b_path: str, annotated_pdf_a_path: str, structured_summary: str, llm_summary: str, detailed_diffs: dict):
    """匯出所有報告檔案"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 寫入詳細的 JSON 報告
    json_path = output_path / "detailed_report.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        # Pandas 物件可能無法直接序列化，先做簡單轉換
        if 'tables' in detailed_diffs:
             for table_diff in detailed_diffs['tables']:
                 if 'pandas_diff' in table_diff:
                     table_diff['pandas_diff'] = str(table_diff['pandas_diff'])
        json.dump(detailed_diffs, f, indent=2, ensure_ascii=False)
    print(f"✅ Detailed JSON report saved to: {json_path}")

    # 2. 寫入 Markdown 報告
    md_report_path = output_path / "summary_report.md"
    report_content = f"{structured_summary}\n\n## III. AI-Generated Summary\n\n{llm_summary}"
    with open(md_report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"✅ Markdown summary saved to: {md_report_path}")

    # 記錄標註檔路徑（方便上層使用）
    return {
        "annotated_pdf_b": str(annotated_pdf_b_path),
        "annotated_pdf_a": str(annotated_pdf_a_path),
        "summary_md": str(md_report_path),
        "detailed_json": str(json_path)
    }

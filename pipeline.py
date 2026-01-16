# pipeline.py
from pathlib import Path
import os
import json

from utils import (
    pdf_utils,
    matcher,
    differ,
    annotator,
    exporter,
)


def print_and_save_json(data, title, filename, output_dir, max_items=3):
    """Pretty-print title and save JSON to output_dir."""
    print("-" * 20)
    print(f"OUTPUT FOR: {title}")
    print("-" * 20)

    filepath = Path(output_dir) / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Full data saved to: {filepath}\n")


def run_pipeline(pdf_path_a, pdf_path_b, output_dir, progress_cb=None, text_threshold=matcher.TEXT_SIMILARITY_THRESHOLD, image_threshold=matcher.IMAGE_PHASH_THRESHOLD):
    """Execute the PDF comparison pipeline and return output paths."""

    def report(step, status="running", message=""):
        if progress_cb:
            progress_cb(step, status, message)

    report("extract")
    print("======== [Step 1: Extracting Content] ========")
    content_a = pdf_utils.extract_content(pdf_path_a, image_output_dir=output_dir)
    content_b = pdf_utils.extract_content(pdf_path_b, image_output_dir=output_dir)
    print_and_save_json(content_a, "Content of PDF A", "1_extracted_content_a.json", output_dir)
    print_and_save_json(content_b, "Content of PDF B", "1_extracted_content_b.json", output_dir)

    report("match")
    print("\n======== [Step 2: Matching Elements] ========")
    matched_data = matcher.match_all(content_a, content_b, text_threshold=text_threshold, image_threshold=image_threshold)
    matched_data_for_json = {
        key: {
            "matched_pairs": value[0],
            "new_in_b": value[1],
            "deleted_from_a": value[2],
        }
        for key, value in matched_data.items()
    }
    print_and_save_json(matched_data_for_json, "Matching Results", "2_matched_data.json", output_dir)

    report("diff")
    print("\n======== [Step 3: Analyzing Differences] ========")
    diffs = differ.diff_all(matched_data)
    print_and_save_json(diffs, "Difference Analysis Results", "3_diff_results.json", output_dir)

    structured_summary = "# PDF Comparison Report\n\n_Summary generation disabled._"
    llm_summary = "LLM summary disabled."

    report("annotate")
    print("\n======== [Step 5: Annotating PDF] ========")
    annotated_pdf_b_path = Path(output_dir) / f"{Path(pdf_path_b).stem}_annotated_b.pdf"
    annotated_pdf_a_path = Path(output_dir) / f"{Path(pdf_path_a).stem}_annotated_a.pdf"
    annotator.annotate_pdf(pdf_path_b, str(annotated_pdf_b_path), diffs, matched_data, perspective="b")
    annotator.annotate_pdf(pdf_path_a, str(annotated_pdf_a_path), diffs, matched_data, perspective="a")

    report("export")
    print("\n======== [Step 6: Exporting Reports] ========")
    all_diffs_details = {
        "new_paragraphs": matched_data["paragraphs"][1],
        "deleted_paragraphs": matched_data["paragraphs"][2],
        "modified_paragraphs": diffs["paragraphs"],
        "new_images": matched_data["images"][1],
        "deleted_images": matched_data["images"][2],
        "modified_images": diffs["images"],
        "new_tables": matched_data["tables"][1],
        "deleted_tables": matched_data["tables"][2],
        "modified_tables": diffs["tables"],
    }

    exporter.export_report(
        output_dir,
        annotated_pdf_b_path=str(annotated_pdf_b_path),
        annotated_pdf_a_path=str(annotated_pdf_a_path),
        structured_summary=structured_summary,
        llm_summary=llm_summary,
        detailed_diffs=all_diffs_details,
    )

    report("done", status="done")
    print("\n🎉 Comparison process completed successfully!")
    print(f"Find all reports in the '{output_dir}' directory.")

    return {
        "output_dir": str(Path(output_dir)),
        "annotated_pdf_b": str(annotated_pdf_b_path),
        "annotated_pdf_a": str(annotated_pdf_a_path),
        "extracted_a": str(Path(output_dir) / "1_extracted_content_a.json"),
        "extracted_b": str(Path(output_dir) / "1_extracted_content_b.json"),
        "matched": str(Path(output_dir) / "2_matched_data.json"),
        "diffs": str(Path(output_dir) / "3_diff_results.json"),
        "summary_md": str(Path(output_dir) / "summary_report.md"),
        "detailed_json": str(Path(output_dir) / "detailed_report.json"),
    }

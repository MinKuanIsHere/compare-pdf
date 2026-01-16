# main.py
"""
Thin CLI entrypoint to run the PDF comparison pipeline.
Usage:
    python main.py [pdf_a] [pdf_b] [output_dir]
Defaults:
    pdf_a = ./data/fileA.pdf
    pdf_b = ./data/fileB.pdf
    output_dir = ./output
"""
import os
import sys
from pathlib import Path

from pipeline import run_pipeline


def main():
    pdf_path_a = sys.argv[1] if len(sys.argv) > 1 else "./data/fileA.pdf"
    pdf_path_b = sys.argv[2] if len(sys.argv) > 2 else "./data/fileB.pdf"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"

    if not (os.path.exists(pdf_path_a) and os.path.exists(pdf_path_b)):
        print("❌ Error: Make sure input files exist.")
        print(f"Checked path A: {os.path.abspath(pdf_path_a)}")
        print(f"Checked path B: {os.path.abspath(pdf_path_b)}")
        sys.exit(1)

    run_pipeline(pdf_path_a, pdf_path_b, output_dir)


if __name__ == "__main__":
    main()

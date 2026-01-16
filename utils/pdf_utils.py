# utils/pdf_utils.py
import fitz  # PyMuPDF
import hashlib
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
import imagehash
from PIL import Image
import io

def extract_content(pdf_path: str, image_output_dir: str) -> Dict[str, List[Dict]]:
    """
    從 PDF 提取文字、圖片、表格，並為每個元素生成 UID 和必要特徵。
    """
    doc = fitz.open(pdf_path)
    pdf_name = Path(pdf_path).stem
    
    # 準備圖片儲存目錄
    image_folder = Path(image_output_dir) / pdf_name
    image_folder.mkdir(parents=True, exist_ok=True)

    all_tables = []
    all_images = []
    
    # 1. 優先提取表格和圖片資訊
    for page_num, page in enumerate(doc):
        # 提取表格
        tables_on_page = page.find_tables()
        for tbl_idx, table in enumerate(tables_on_page):
            all_tables.append({
                "uid": f"p{page_num}_tbl{tbl_idx}",
                "page": page_num,
                "bbox": list(table.bbox),
                "content": table.extract(),  # 儲存結構化資料
                "content_str": "\n".join([",".join(map(str, row)) for row in table.extract()])
            })

        # 提取圖片
        images_on_page = page.get_images(full=True)
        for img_idx, img in enumerate(images_on_page):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # 計算 phash
                pil_image = Image.open(io.BytesIO(image_bytes))
                phash = imagehash.phash(pil_image)

                img_path = image_folder / f"p{page_num}_img{img_idx}.{base_image['ext']}"
                with open(img_path, "wb") as f:
                    f.write(image_bytes)

                all_images.append({
                    "uid": f"p{page_num}_img{img_idx}",
                    "page": page_num,
                    "bbox": list(page.get_image_bbox(img).irect),
                    "path": str(img_path),
                    "phash": str(phash)
                })
            except Exception as e:
                print(f"Warning: Could not process image {img_idx} on page {page_num}: {e}")

    # 2. 提取文字段落，並過濾掉表格內的文字
    all_paragraphs = []
    para_index = 0
    for page_num, page in enumerate(doc):
        table_bboxes_on_page = [t['bbox'] for t in all_tables if t['page'] == page_num]
        
        blocks = page.get_text("blocks")
        for block in blocks:
            # block format: (x0, y0, x1, y1, text, block_no, block_type)
            block_bbox = fitz.Rect(block[0], block[1], block[2], block[3])
            text = block[4].strip()
            
            if not text:
                continue

            is_in_table = any(block_bbox.intersects(fitz.Rect(bbox)) for bbox in table_bboxes_on_page)
            
            if not is_in_table:
                # 簡單地將每個文字區塊視為一個段落，可以根據需求合併
                all_paragraphs.append({
                    "uid": f"p{page_num}_para{para_index}",
                    "page": page_num,
                    "bbox": list(block_bbox),
                    "text": text
                })
                para_index += 1
                
    doc.close()

    print(f"✅ Extracted from {pdf_name}: {len(all_paragraphs)} paragraphs, {len(all_images)} images, {len(all_tables)} tables.")
    
    return {
        "paragraphs": all_paragraphs,
        "images": all_images,
        "tables": all_tables
    }
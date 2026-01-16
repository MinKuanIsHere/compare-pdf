# utils/annotator.py
import fitz

# Semi-transparent palettes
COLOR_ADDED = (0.2, 0.8, 0.4)   # soft green
COLOR_DELETED = (0.95, 0.3, 0.3) # soft red
COLOR_MODIFIED = (0.25, 0.55, 0.9) # soft blue
ANNOT_OPACITY = 0.5

def _wrap_items_with_kind(items, kind):
    for it in items:
        yield {**it, "_kind": kind}

def annotate_pdf(pdf_path: str, output_path: str, diffs: dict, matched_data: dict, perspective: str = "b"):
    """
    在指定 PDF 上標註差異。
    perspective:
        - "b": 新增/修改（B 視角：新增=綠、修改=藍）
        - "a": 刪除/修改（A 視角：刪除=紅、修改=藍）
    """
    doc = fitz.open(pdf_path)
    
    if perspective == "b":
        new_items = list(_wrap_items_with_kind(matched_data['paragraphs'][1] + matched_data['images'][1] + matched_data['tables'][1], "added"))
    else:
        # A 視角：刪除 + 修改
        new_items = list(_wrap_items_with_kind(matched_data['paragraphs'][2] + matched_data['images'][2] + matched_data['tables'][2], "deleted"))
    modified_items = list(_wrap_items_with_kind(diffs['paragraphs'] + diffs['images'] + diffs['tables'], "modified"))

    print(f"\nAnnotating PDF ({perspective} view)... Found {len(new_items)} new items and {len(modified_items)} modified items.")

    for item in new_items + modified_items:
        try:
            page = doc.load_page(item['page'])
            bbox = fitz.Rect(item['bbox'])
            
            if bbox.is_infinite or bbox.is_empty:
                print(f"Warning: Skipping annotation for invalid bbox on page {item['page']}: {item['bbox']}")
                continue

            kind = item.get("_kind", "modified")
            if kind == "added":
                color = COLOR_ADDED
            elif kind == "deleted":
                color = COLOR_DELETED
            else:
                color = COLOR_MODIFIED

            annot = page.add_rect_annot(bbox)
            annot.set_colors(stroke=color, fill=color)
            annot.set_opacity(ANNOT_OPACITY)
            annot.set_border(width=0.5, dashes=None)
            annot.update()

        except Exception as e:
            print(f"Warning: Could not annotate item (uid: {item.get('uid_b', 'N/A')}) on page {item.get('page', 'N/A')}. Error: {e}")

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    print(f"✅ Annotated PDF saved to: {output_path}")
    return output_path

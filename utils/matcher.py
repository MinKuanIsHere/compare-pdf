# utils/matcher.py
import difflib
import imagehash
import re # 導入正則表達式模組

# --- Constants ---
TEXT_SIMILARITY_THRESHOLD = 0.8  # 文本相似度閾值
IMAGE_PHASH_THRESHOLD = 5        # 感知雜湊漢明距離閾值

# ===== 文字正規化函數 =====
def normalize_text(text: str) -> str:
    """
    對文字進行正規化，以提高比對準確性。
    1. 移除首尾空白。
    2. 將所有空白字符 (包括空格、換行、tab) 的連續序列替換為單一空格。
    """
    if not text:
        return ""
    # 使用正則表達式 re.sub 來替換所有空白字符序列 (\s+) 為一個空格
    normalized = re.sub(r'\s+', ' ', text).strip()
    return normalized
# =================================

def match_elements(items_a: list, items_b: list, match_func, **kwargs):
    """通用配對函數"""
    b_items_pool = list(items_b)
    matched_pairs = []
    unmatched_a = []

    for item_a in items_a:
        best_match = None
        highest_score = -1
        
        # 為了提升效率，預先正規化 item_a 的文字
        normalized_text_a = None
        if 'text' in item_a:
            normalized_text_a = normalize_text(item_a['text'])

        for i, item_b in enumerate(b_items_pool):
            # 傳遞預先處理好的 item_a 文字，避免重複計算
            score = match_func(item_a, item_b, normalized_a=normalized_text_a, **kwargs)
            if score > highest_score:
                highest_score = score
                best_match = (i, item_b)

        if highest_score >= kwargs.get('threshold', 0.8):
            matched_pairs.append({
                "item_a": item_a,
                "item_b": best_match[1],
                "confidence": highest_score
            })
            b_items_pool.pop(best_match[0])
        else:
            unmatched_a.append(item_a)
            
    unmatched_b = b_items_pool
    
    return matched_pairs, unmatched_b, unmatched_a

# --- Matcher Functions ---
# ===== 文字比對評分函數 =====
def _text_match_score(para_a, para_b, **kwargs):
    """計算兩個段落的相似度分數，使用正規化後的文字"""
    
    # 接收預先處理好的 a_text，如果沒有則自己處理
    text_a_normalized = kwargs.get('normalized_a')
    if text_a_normalized is None:
        text_a_normalized = normalize_text(para_a['text'])
        
    text_b_normalized = normalize_text(para_b['text'])
    
    # 如果正規化後兩個字串完全相等，給予最高分，以應對只有空白差異的情況
    if text_a_normalized == text_b_normalized:
        return 1.0
        
    return difflib.SequenceMatcher(None, text_a_normalized, text_b_normalized).ratio()
# ===================================

def _image_match_score(img_a, img_b, **kwargs):
    """計算兩張圖片的相似度分數 (基於 pHash)"""
    hash_a = imagehash.hex_to_hash(img_a['phash'])
    hash_b = imagehash.hex_to_hash(img_b['phash'])
    distance = hash_a - hash_b
    if distance <= kwargs.get('threshold', IMAGE_PHASH_THRESHOLD):
        return 1.0 - (distance / (kwargs.get('threshold', IMAGE_PHASH_THRESHOLD) + 1))
    return 0.0

def _table_match_score(table_a, table_b, **kwargs):
    """計算兩個表格的相似度分數 (基於內容字串)"""
    # 表格內容也適用正規化
    text_a_normalized = normalize_text(table_a['content_str'])
    text_b_normalized = normalize_text(table_b['content_str'])
    return difflib.SequenceMatcher(None, text_a_normalized, text_b_normalized).ratio()


# --- Public API ---
def match_all(content_a: dict, content_b: dict, text_threshold: float = TEXT_SIMILARITY_THRESHOLD, image_threshold: int = IMAGE_PHASH_THRESHOLD):
    # ... (此函數無需修改) ...
    print("\nMatching paragraphs...")
    matched_paras, new_paras, deleted_paras = match_elements(
        content_a['paragraphs'], content_b['paragraphs'], _text_match_score, threshold=text_threshold
    )
    
    print("Matching images...")
    matched_images, new_images, deleted_images = match_elements(
        content_a['images'], content_b['images'], _image_match_score, threshold=image_threshold
    )
    
    print("Matching tables...")
    matched_tables, new_tables, deleted_tables = match_elements(
        content_a['tables'], content_b['tables'], _table_match_score, threshold=text_threshold
    )
    
    return {
        "paragraphs": (matched_paras, new_paras, deleted_paras),
        "images": (matched_images, new_images, deleted_images),
        "tables": (matched_tables, new_tables, deleted_tables)
    }

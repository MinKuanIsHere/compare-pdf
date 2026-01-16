# utils/differ.py
import pandas as pd

def diff_all(matched_data: dict):
    """對所有已配對的項目進行差異分析"""
    print("\nAnalyzing differences in paragraphs...")
    para_diffs = diff_paragraphs(matched_data['paragraphs'][0])
    
    print("Analyzing differences in images...")
    image_diffs = diff_images(matched_data['images'][0])
    
    print("Analyzing differences in tables...")
    table_diffs = diff_tables(matched_data['tables'][0])
    
    return {
        "paragraphs": para_diffs,
        "images": image_diffs,
        "tables": table_diffs
    }

def diff_paragraphs(matched_paras: list) -> list:
    """分析段落文字差異"""
    diffs = []
    for pair in matched_paras:
        if pair['confidence'] < 1.0: # 只有在不完全相同時才分析
            diffs.append({
                "uid_a": pair['item_a']['uid'],
                "uid_b": pair['item_b']['uid'],
                "page": pair['item_b']['page'],
                "bbox": pair['item_b']['bbox'],
                "text_a": pair['item_a']['text'],
                "text_b": pair['item_b']['text'],
                "diff_ratio": pair['confidence']
            })
    return diffs

def diff_images(matched_images: list) -> list:
    """分析圖片差異 (pHash)"""
    diffs = []
    for pair in matched_images:
        if pair['confidence'] < 1.0: # 只有 pHash 不同時才視為修改
            diffs.append({
                "uid_a": pair['item_a']['uid'],
                "uid_b": pair['item_b']['uid'],
                "page": pair['item_b']['page'],
                "bbox": pair['item_b']['bbox'],
                "phash_a": pair['item_a']['phash'],
                "phash_b": pair['item_b']['phash'],
                # 此處為呼叫 MLLM 進行視覺比較預留位置
                "llm_analysis": "Placeholder: MLLM analysis of visual difference."
            })
    return diffs

def diff_tables(matched_tables: list) -> list:
    """分析表格差異 (使用 pandas)"""
    diffs = []
    for pair in matched_tables:
        if pair['confidence'] < 1.0:
            df_a = pd.DataFrame(pair['item_a']['content'])
            df_b = pd.DataFrame(pair['item_b']['content'])
            
            try:
                # pandas compare 需要相同的 index 和 columns
                # 這裡做一個簡化，實際可能需要更複雜的對齊邏輯
                if df_a.shape == df_b.shape:
                    df_a.columns = range(df_a.shape[1])
                    df_b.columns = range(df_b.shape[1])
                    comparison = df_b.compare(df_a)
                    pandas_diff_str = comparison.to_string()
                else:
                    pandas_diff_str = "Table shapes are different."
            except Exception as e:
                pandas_diff_str = f"Could not compare DataFrames: {e}"

            diffs.append({
                "uid_a": pair['item_a']['uid'],
                "uid_b": pair['item_b']['uid'],
                "page": pair['item_b']['page'],
                "bbox": pair['item_b']['bbox'],
                "pandas_diff": pandas_diff_str,
                 # 此處為呼叫 LLM 進行差異解讀預留位置
                "llm_interpretation": "Placeholder: LLM interpretation of table changes."
            })
    return diffs
# from xgboost import XGBRegressor
from pathlib import Path
import pandas as pd
import joblib

def predict(features, strategy):
    MODEL_PATH = Path("src/dashboard/models/")
    
    model = joblib.load(MODEL_PATH/"lcp_model.joblib")
    row = pd.json_normalize(features)
    
    drop_cols = [
        'performance_score', 
        'largest-contentful-paint',
        'cumulative-layout-shift',
        'first-contentful-paint',
        'total-blocking-time',
        'speed-index', 
        'interactive',
        'mainthread_garbageCollection',
        'EXPERIMENTAL_TIME_TO_FIRST_BYTE',
        'INTERACTION_TO_NEXT_PAINT']
    row = row.drop(columns=drop_cols)
    
    if strategy == "desktop":
        row["strategy_desktop"] = 1
        row["strategy_mobile"] = 0
    else:
        row["strategy_desktop"] = 0
        row["strategy_mobile"] = 1
    
    feature_columns = [
        'total-byte-weight',
        'dom-size-insight',
        'mainthread_other',
        'mainthread_paintCompositeRender',
        'mainthread_parseHTML',
        'mainthread_scriptEvaluation',
        'mainthread_scriptParseCompile',
        'mainthread_styleLayout',
        'network-server-latency',
        'resource_document_bytes',
        'resource_document_requests',
        'resource_font_bytes',
        'resource_font_requests',
        'resource_image_bytes',
        'resource_image_requests',
        'resource_media_bytes',
        'resource_media_requests',
        'resource_other_bytes',
        'resource_other_requests',
        'resource_script_bytes',
        'resource_script_requests',
        'resource_stylesheet_bytes',
        'resource_stylesheet_requests',
        'resource_third-party_bytes',
        'resource_third-party_requests',
        'resource_total_bytes',
        'resource_total_requests',
        'unminified-css',
        'unminified-javascript',
        'unused-css-rules',
        'unused-css-rules_savings_bytes',
        'unused-css-rules_savings_ms',
        'unused-javascript',
        'unused-javascript_savings_bytes',
        'unused-javascript_savings_ms',
        'strategy_desktop',
        'strategy_mobile'
    ]
    
    row = row.reindex(columns=feature_columns)
    
    if row.isnull().values.any():
        print("None")
        return None
    else:
        pred = model.predict(row)
        print(pred)
        return pred
        
# if __name__ == "__main__":

# 	predict({ "EXPERIMENTAL_TIME_TO_FIRST_BYTE": 330, "INTERACTION_TO_NEXT_PAINT": 20, "cumulative-layout-shift": 0.133084, "dom-size-insight": 1616, "first-contentful-paint": 685.0119688106245, "interactive": 9594.275269173413, "largest-contentful-paint": 1015.0175296822713, "mainthread_garbageCollection": 384.04299999999915, "mainthread_other": 2070.4600000000205, "mainthread_paintCompositeRender": 130.00000000001066, "mainthread_parseHTML": 106.4249999999999, "mainthread_scriptEvaluation": 3590.7880000001937, "mainthread_scriptParseCompile": 764.9209999999994, "mainthread_styleLayout": 394.5359999999999, "network-server-latency": 19, "performance_score": 0.59, "resource_document_bytes": 306696, "resource_document_requests": 123, "resource_font_bytes": 168763, "resource_font_requests": 6, "resource_image_bytes": 223127, "resource_image_requests": 213, "resource_media_bytes": 0, "resource_media_requests": 0, "resource_other_bytes": 457190, "resource_other_requests": 472, "resource_script_bytes": 2681270, "resource_script_requests": 75, "resource_stylesheet_bytes": 37043, "resource_stylesheet_requests": 4, "resource_third-party_bytes": 3162998, "resource_third-party_requests": 855, "resource_total_bytes": 3874089, "resource_total_requests": 893, "speed-index": 2730.3649341548203, "total-blocking-time": 855.0000000000027, "total-byte-weight": 3874089, "unminified-css": 0, "unminified-javascript": 0, "unused-css-rules": 80, "unused-css-rules_savings_bytes": 16852, "unused-css-rules_savings_ms": 80, "unused-javascript": 0, "unused-javascript_savings_bytes": 870800, "unused-javascript_savings_ms": 0 }, "desktop")
"""Translation integrity tests — parse T/CAT_TR from source (no app import needed)."""
import os
import re
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")


def _extract_dict(name):
    """Extract a top-level dict literal named `name` from app.py source via AST."""
    src = open(APP_PATH).read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name and isinstance(node.value, ast.Dict):
                    return _eval_dict(node.value)
    raise KeyError(f"dict {name} not found")


def _eval_dict(dnode):
    out = {}
    for k, v in zip(dnode.keys, dnode.values):
        key = k.value if isinstance(k, ast.Constant) else ast.literal_eval(k)
        if isinstance(v, ast.Dict):
            out[key] = {ik.value: iv.value for ik, iv in zip(v.keys, v.values)}
        else:
            out[key] = ast.literal_eval(v)
    return out


def test_all_translation_keys_have_three_languages():
    T = _extract_dict("T")
    langs = ("fa", "de", "en")
    for key, val in T.items():
        for lang in langs:
            assert lang in val, f"T['{key}'] missing '{lang}'"
        assert val["fa"].strip(), f"T['{key}'] empty fa"


def test_category_translations_complete():
    CAT_TR = _extract_dict("CAT_TR")
    langs = ("fa", "de", "en")
    for cat, val in CAT_TR.items():
        for lang in langs:
            assert lang in val, f"CAT_TR['{cat}'] missing '{lang}'"


def test_no_duplicate_translation_keys():
    T = _extract_dict("T")
    keys = list(T.keys())
    assert len(keys) == len(set(keys)), "Duplicate keys in T"


def test_widget_labels_contain_no_hardcoded_persian():
    src = open(APP_PATH).read()
    body = src[src.find("def tt("):]
    pattern = re.compile(
        r'st\.(selectbox|text_input|number_input|date_input|expander|checkbox|file_uploader|button)\("[^"]*[\u0600-\u06FF][^"]*"'
    )
    bad = set(pattern.findall(body))
    assert not bad, f"Hardcoded Persian widget labels: {bad}"
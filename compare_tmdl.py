"""
compare_tmdl.py (versão modular)
Permite ser usado via linha de comando OU importado como módulo no Streamlit.
"""

import os
import sys
import json
import difflib
import re
from pathlib import Path

# ----------------------------
# Funções utilitárias
# ----------------------------

def pick_folder_gui(prompt="Selecione uma pasta (pressione Cancel para digitar o caminho):"):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title=prompt)
        root.destroy()
        if path:
            return path
    except Exception:
        pass
    return input(f"{prompt}\nCaminho: ").strip()

def find_semantic_model_folder(root_path: str):
    root = Path(root_path)
    if not root.exists():
        return None
    for p in root.rglob("*"):
        if p.is_dir() and p.name.lower().endswith(".semanticmodel"):
            return str(p)
    if root.name.lower().endswith(".semanticmodel") and root.is_dir():
        return str(root)
    return None

def get_definition_tables_folder(semantic_model_folder: str):
    cand1 = Path(semantic_model_folder) / "definition" / "tables"
    cand2 = Path(semantic_model_folder) / "definition"
    if cand1.exists() and cand1.is_dir():
        return str(cand1)
    if cand2.exists() and cand2.is_dir():
        return str(cand2)
    return None

def list_tmdl_files(def_tables_folder: str):
    p = Path(def_tables_folder)
    files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".tmdl"]
    return sorted(files, key=lambda x: x.name.lower())

def parse_tmdl_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    columns = set()
    measures = set()

    table_pattern = re.compile(r"^\s*table\s+([A-Za-z0-9_ ]+)", re.MULTILINE)
    column_pattern = re.compile(r"^\s*column\s+([A-Za-z0-9_]+)", re.MULTILINE)
    measure_pattern = re.compile(r"^\s*measure\s+'?([^'=]+?)'?\s*=", re.MULTILINE)

    tables = table_pattern.findall(text)
    columns = set(column_pattern.findall(text))
    measures = set(measure_pattern.findall(text))

    name = path.stem
    if tables:
        name = tables[0].strip()

    return {
        "name": name,
        "file": str(path),
        "text": text,
        "columns": columns,
        "measures": measures,
        "raw_json": None
    }

def compare_models(source_files, target_files):
    source_names = set(source_files.keys())
    target_names = set(target_files.keys())

    only_in_source = sorted(source_names - target_names)
    only_in_target = sorted(target_names - source_names)
    common = sorted(source_names & target_names)

    identical = []
    different = []
    diffs_details = {}

    for name in common:
        src = source_files[name]
        tgt = target_files[name]
        if src["text"] == tgt["text"]:
            identical.append(name)
            continue

        src_cols = src["columns"]
        tgt_cols = tgt["columns"]
        src_meas = src["measures"]
        tgt_meas = tgt["measures"]

        cols_only_src = sorted(src_cols - tgt_cols)
        cols_only_tgt = sorted(tgt_cols - src_cols)
        meas_only_src = sorted(src_meas - tgt_meas)
        meas_only_tgt = sorted(tgt_meas - src_meas)

        textual_diff = []
        if not (src_cols or tgt_cols or src_meas or tgt_meas):
            text_diff = difflib.unified_diff(
                src["text"].splitlines(keepends=True),
                tgt["text"].splitlines(keepends=True),
                fromfile=f"{name} (source)",
                tofile=f"{name} (target)",
                lineterm=""
            )
            textual_diff = list(text_diff)[:400]

        if cols_only_src or cols_only_tgt or meas_only_src or meas_only_tgt or textual_diff:
            different.append(name)
            diffs_details[name] = {
                "cols_only_in_source": cols_only_src,
                "cols_only_in_target": cols_only_tgt,
                "measures_only_in_source": meas_only_src,
                "measures_only_in_target": meas_only_tgt,
                "textual_diff_snippet": textual_diff
            }
        else:
            identical.append(name)

    return {
        "counts": {
            "source_total": len(source_names),
            "target_total": len(target_names),
            "identical": len(identical),
            "different": len(different),
            "only_in_source": len(only_in_source),
            "only_in_target": len(only_in_target)
        },
        "lists": {
            "identical": identical,
            "different": different,
            "only_in_source": only_in_source,
            "only_in_target": only_in_target
        },
        "details": diffs_details
    }

# ----------------------------
# Nova função principal modular
# ----------------------------

def compare_tmdl(model_a_root: str, model_b_root: str):
    """
    Executa comparação de dois modelos TMDL e retorna o relatório completo (dict).
    Pode ser usada diretamente no Streamlit.
    """
    a_sem = find_semantic_model_folder(model_a_root)
    b_sem = find_semantic_model_folder(model_b_root)
    if not a_sem or not b_sem:
        raise ValueError("Pasta .SemanticModel não encontrada em um dos modelos.")

    a_def = get_definition_tables_folder(a_sem)
    b_def = get_definition_tables_folder(b_sem)
    if not a_def or not b_def:
        raise ValueError("Pasta definition/tables não encontrada em um dos modelos.")

    a_files = list_tmdl_files(a_def)
    b_files = list_tmdl_files(b_def)

    source_parsed = {parse_tmdl_file(f)["name"]: parse_tmdl_file(f) for f in a_files}
    target_parsed = {parse_tmdl_file(f)["name"]: parse_tmdl_file(f) for f in b_files}

    report = compare_models(source_parsed, target_parsed)
    return report

# ----------------------------
# Execução direta (CLI)
# ----------------------------
def main():
    print("=== Comparador de modelos .tmdl ===")
    print("Escolha o Modelo A (fonte):")
    model_a_root = pick_folder_gui("Selecione a pasta raiz do Modelo A (ou digite o caminho)")
    if not model_a_root:
        sys.exit(1)
    print("Escolha o Modelo B (central):")
    model_b_root = pick_folder_gui("Selecione a pasta raiz do Modelo B (ou digite o caminho)")
    if not model_b_root:
        sys.exit(1)

    report = compare_tmdl(model_a_root, model_b_root)
    counts = report["counts"]
    lists = report["lists"]

    print("\n=== RESUMO ===")
    print(f"Tabelas no Modelo A: {counts['source_total']}")
    print(f"Tabelas no Modelo B: {counts['target_total']}")
    print(f"✅ Iguais: {counts['identical']}")
    print(f"⚠️ Diferentes: {counts['different']}")
    print(f"➕ Novas no A: {counts['only_in_source']}")
    print(f"➖ Faltando no A: {counts['only_in_target']}")

    # detalhes
    print("\n=== DETALHES DAS DIFERENÇAS ===")

    if lists["only_in_source"]:
        print("\nTabelas apenas no Modelo A:")
        for t in lists["only_in_source"]:
            print("  -", t)

    if lists["only_in_target"]:
        print("\nTabelas apenas no Modelo B:")
        for t in lists["only_in_target"]:
            print("  -", t)

    if lists["different"]:
        print("\nTabelas diferentes (com diferenças em colunas/measures/text):")
        for t in lists["different"]:
            d = report["details"].get(t, {})
            print(f"- {t}:")
            if d.get("cols_only_in_source"):
                print("    • Colunas só no A:", ", ".join(d["cols_only_in_source"]))
            if d.get("cols_only_in_target"):
                print("    • Colunas só no B:", ", ".join(d["cols_only_in_target"]))
            if d.get("measures_only_in_source"):
                print("    • Medidas só no A:", ", ".join(d["measures_only_in_source"]))
            if d.get("measures_only_in_target"):
                print("    • Medidas só no B:", ", ".join(d["measures_only_in_target"]))
            if d.get("textual_diff_snippet"):
                print("    • Trecho textual (diff) disponível — use mostrar diff completo separadamente se precisar.")

    print("\nFim da comparação.")



if __name__ == "__main__":
    main()

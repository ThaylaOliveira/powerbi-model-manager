# app.py
import streamlit as st
from pathlib import Path
import tempfile
import zipfile

from compare_tmdl import (
    find_semantic_model_folder,
    get_definition_tables_folder,
    list_tmdl_files,
    parse_tmdl_file,
    compare_models,
)
from merge_tmdl import merge_models

st.set_page_config(page_title="Power BI TMDL Manager", layout="wide")
st.title("Power BI Model Control")

# ---------------------
# Upload de modelos
# ---------------------
st.header("Enviar Modelos")

uploaded_a = st.file_uploader("Upload do Modelo A (.zip)", type=["zip"])
uploaded_b = st.file_uploader("Upload do Modelo B (.zip)", type=["zip"])

# Função para salvar e extrair ZIP
def save_and_extract_zip(uploaded_file):
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / uploaded_file.name
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
    return tmp_dir

model_a_root = save_and_extract_zip(uploaded_a) if uploaded_a else None
model_b_root = save_and_extract_zip(uploaded_b) if uploaded_b else None

# ---------------------
# Comparação
# ---------------------
comparison_text = ""

compare_button = st.button("Comparar Modelos")
if compare_button:
    if not model_a_root or not model_b_root:
        st.error("Envie os dois arquivos ZIP antes de comparar.")
    else:
        with st.spinner("Comparando modelos..."):
            # localizar .SemanticModel
            a_sem = find_semantic_model_folder(model_a_root)
            b_sem = find_semantic_model_folder(model_b_root)

            if not a_sem or not b_sem:
                st.error("Não foi possível localizar a pasta .SemanticModel em A ou B.")
            else:
                # definition/tables
                a_def = get_definition_tables_folder(a_sem)
                b_def = get_definition_tables_folder(b_sem)

                if not a_def or not b_def:
                    st.error("Não foi possível localizar definition/tables em A ou B.")
                else:
                    # listar arquivos e parse
                    a_files = list_tmdl_files(a_def)
                    b_files = list_tmdl_files(b_def)

                    source_parsed = {f.stem: parse_tmdl_file(f) for f in a_files}
                    target_parsed = {f.stem: parse_tmdl_file(f) for f in b_files}

                    report = compare_models(source_parsed, target_parsed)
                    counts = report["counts"]

                    # Resumo
                    st.subheader("Resumo da Comparação")
                    st.write(f"Tabelas no Modelo A: {counts['source_total']}")
                    st.write(f"Tabelas no Modelo B: {counts['target_total']}")
                    st.write(f"✅ Iguais: {counts['identical']}")
                    st.write(f"⚠️ Diferentes: {counts['different']}")
                    st.write(f"➕ Apenas no A: {counts['only_in_source']}")
                    st.write(f"➖ Apenas no B: {counts['only_in_target']}")

                    # Detalhes
                    if lists := report.get("lists"):
                        if lists["only_in_source"]:
                            st.subheader("Tabelas apenas no Modelo A")
                            for t in lists["only_in_source"]:
                                st.write("-", t)
                        if lists["only_in_target"]:
                            st.subheader("Tabelas apenas no Modelo B")
                            for t in lists["only_in_target"]:
                                st.write("-", t)

                    if report["details"]:
                        st.subheader("Diferenças detalhadas por tabela")
                        for t, d in report["details"].items():
                            st.markdown(f"**{t}**")
                            if d.get("cols_only_in_source"):
                                st.write("Colunas só no A:", d["cols_only_in_source"])
                            if d.get("cols_only_in_target"):
                                st.write("Colunas só no B:", d["cols_only_in_target"])
                            if d.get("measures_only_in_source"):
                                st.write("Medidas só no A:", d["measures_only_in_source"])
                            if d.get("measures_only_in_target"):
                                st.write("Medidas só no B:", d["measures_only_in_target"])
                            if d.get("textual_diff_snippet"):
                                st.write("Trecho textual diff disponível (resumido)")

                    # Gerar texto para download
                    lines = []
                    lines.append(f"Tabelas no Modelo A: {counts['source_total']}")
                    lines.append(f"Tabelas no Modelo B: {counts['target_total']}")
                    lines.append(f"Iguais: {counts['identical']}")
                    lines.append(f"Diferentes: {counts['different']}")
                    lines.append(f"Apenas no A: {counts['only_in_source']}")
                    lines.append(f"Apenas no B: {counts['only_in_target']}\n")

                    if lists := report.get("lists"):
                        if lists["only_in_source"]:
                            lines.append("Tabelas apenas no Modelo A:")
                            lines.extend(f"  - {t}" for t in lists["only_in_source"])
                        if lists["only_in_target"]:
                            lines.append("Tabelas apenas no Modelo B:")
                            lines.extend(f"  - {t}" for t in lists["only_in_target"])

                    if report["details"]:
                        lines.append("\nDiferenças detalhadas por tabela:")
                        for t, d in report["details"].items():
                            lines.append(f"- {t}:")
                            if d.get("cols_only_in_source"):
                                lines.append(f"    • Colunas só no A: {', '.join(d['cols_only_in_source'])}")
                            if d.get("cols_only_in_target"):
                                lines.append(f"    • Colunas só no B: {', '.join(d['cols_only_in_target'])}")
                            if d.get("measures_only_in_source"):
                                lines.append(f"    • Medidas só no A: {', '.join(d['measures_only_in_source'])}")
                            if d.get("measures_only_in_target"):
                                lines.append(f"    • Medidas só no B: {', '.join(d['measures_only_in_target'])}")

                    comparison_text = "\n".join(lines)
                    st.session_state["ready_to_merge"] = True

# Botão de download do relatório
if comparison_text:
    st.download_button(
        label="📥 Baixar Resultado da Comparação",
        data=comparison_text,
        file_name="Comparacao_Modelos.txt",
        mime="text/plain"
    )

# ---------------------
# Merge
# ---------------------
if st.session_state.get("ready_to_merge"):
    st.header("Mesclar Modelos")
    merge_button = st.button("Mesclar Modelos")
    if merge_button:
        with st.spinner("Mesclando modelos..."):
            # executa o merge
            result = merge_models(model_a_root, model_b_root)

            st.success("✅ Merge concluído!")
            st.write(f"Tabelas novas: {len(result['novas'])}", result['novas'])
            st.write(f"Tabelas atualizadas: {len(result['atualizadas'])}", result['atualizadas'])

            # pegar a pasta pai do .semanticmodel do Modelo B atualizado
            b_folder = Path(result["destino"]).parent  # aqui pegamos o pai

            # criar ZIP mantendo a estrutura completa do modelo
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for f in b_folder.rglob("*"):
                        zipf.write(f, f.relative_to(b_folder))  # mantém estrutura de pastas

            # abrir o ZIP como bytes para o download
            with open(tmp_zip.name, "rb") as f:
                zip_bytes = f.read()
            
            # botão de download
            st.download_button(
                "📥 Baixar Modelo B Atualizado (ZIP)",
                data=zip_bytes,
                file_name="ModeloB_Atualizado.SemanticModel.zip",
                mime="application/zip"
            )



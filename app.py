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

# ---------------------
# CONFIGURAÇÃO INICIAL
# ---------------------
st.set_page_config(page_title="Power BI Model Control", layout="wide", page_icon="⚙️")

st.markdown(
    """
    <style>
    .main-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f4b400;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: #ccc;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .section {
        background-color: #1E1E1E;
        border-radius: 12px;
        box-shadow: 0 0 10px rgba(255,255,255,0.05);
        margin-bottom: 2rem;
    }
    .footer {
        text-align: center;
        font-size: 0.9rem;
        color: #999;
        margin-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">⚙️ Power BI Model Control</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Compare, mescle e atualize modelos semânticos do Power BI com facilidade.</div>', unsafe_allow_html=True)

# ---------------------
# SIDEBAR - INSTRUÇÕES
# ---------------------

# Estilo para aumentar a largura e personalizar o visual da sidebar
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        width: 400px !important;
        min-width: 400px !important;
        background-color: #181818 !important;
        border-right: 1px solid #333;
        padding: 1rem;
    }
    [data-testid="stSidebar"] * {
        color: #ddd !important;
        font-size: 0.95rem;
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #f4b400 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Conteúdo da sidebar
st.sidebar.header("📘 Instruções de Uso")
st.sidebar.markdown("""
1. **Prepare seus modelos**  
   Exporte dois arquivos `.zip` contendo as pastas do modelo semântico (.pbip) do Power BI.  
   - Modelo **A** → Fonte (modelo mais novo)  
   - Modelo **B** → Destino (modelo base no qual será aplicado o merge)

2. **Etapas do processo**  
   - Vá até a aba **Comparar** para identificar diferenças entre os modelos.  
   - Depois, na aba **Mesclar**, una as tabelas novas e atualizadas no Modelo B.  

3. **Resultado**  
   - Após o merge, você poderá **baixar o novo Modelo B atualizado** em formato `.zip`,  
     pronto para ser substituído no seu projeto Power BI.

💡 **Dica:** Use sempre versões limpas exportadas do Power BI para evitar conflitos.
""")

# ---------------------
# ABAS PRINCIPAIS
# ---------------------
tab1, tab2 = st.tabs(["🔍 Comparar Modelos", "🧩 Mesclar Modelos"])

# ---------------------
# FUNÇÃO DE UPLOAD E EXTRAÇÃO
# ---------------------
def save_and_extract_zip(uploaded_file):
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / uploaded_file.name
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
    return tmp_dir


# ---------------------
# ABA 1 - COMPARAR
# ---------------------
with tab1:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("📂 Enviar Modelos para Comparação")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_a = st.file_uploader("Modelo A (.zip)", type=["zip"], key="upload_a_compare")
    with col2:
        uploaded_b = st.file_uploader("Modelo B (.zip)", type=["zip"], key="upload_b_compare")

    model_a_root = save_and_extract_zip(uploaded_a) if uploaded_a else None
    model_b_root = save_and_extract_zip(uploaded_b) if uploaded_b else None

    comparison_text = ""

    compare_button = st.button("🔍 Comparar Modelos", use_container_width=True)
    if compare_button:
        if not model_a_root or not model_b_root:
            st.error("Envie os dois arquivos ZIP antes de comparar.")
        else:
            with st.spinner("Comparando modelos..."):
                a_sem = find_semantic_model_folder(model_a_root)
                b_sem = find_semantic_model_folder(model_b_root)

                if not a_sem or not b_sem:
                    st.error("Não foi possível localizar a pasta .SemanticModel em A ou B.")
                else:
                    a_def = get_definition_tables_folder(a_sem)
                    b_def = get_definition_tables_folder(b_sem)

                    if not a_def or not b_def:
                        st.error("Não foi possível localizar definition/tables em A ou B.")
                    else:
                        a_files = list_tmdl_files(a_def)
                        b_files = list_tmdl_files(b_def)

                        source_parsed = {f.stem: parse_tmdl_file(f) for f in a_files}
                        target_parsed = {f.stem: parse_tmdl_file(f) for f in b_files}

                        report = compare_models(source_parsed, target_parsed)
                        counts = report["counts"]

                        st.success("✅ Comparação concluída!")
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

    if comparison_text:
        st.download_button(
            "📄 Baixar Resultado da Comparação",
            data=comparison_text,
            file_name="Comparacao_Modelos.txt",
            mime="text/plain",
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------
# ABA 2 - MESCLAR
# ---------------------
with tab2:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("🧩 Mesclar Modelos")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_a_merge = st.file_uploader("Modelo A (.zip)", type=["zip"], key="upload_a_merge")
    with col2:
        uploaded_b_merge = st.file_uploader("Modelo B (.zip)", type=["zip"], key="upload_b_merge")

    model_a_root = save_and_extract_zip(uploaded_a_merge) if uploaded_a_merge else None
    model_b_root = save_and_extract_zip(uploaded_b_merge) if uploaded_b_merge else None

    if st.button("🚀 Executar Merge", use_container_width=True):
        if not model_a_root or not model_b_root:
            st.error("Envie os dois arquivos ZIP antes de mesclar.")
        else:
            with st.spinner("Mesclando modelos..."):
                result = merge_models(model_a_root, model_b_root)
                st.success("✅ Merge concluído com sucesso!")
                st.write(f"Tabelas novas: {len(result['novas'])}", result['novas'])
                st.write(f"Tabelas atualizadas: {len(result['atualizadas'])}", result['atualizadas'])

                b_folder = Path(result["destino"]).parent
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for f in b_folder.rglob("*"):
                            zipf.write(f, f.relative_to(b_folder))

                with open(tmp_zip.name, "rb") as f:
                    zip_bytes = f.read()

                st.download_button(
                    "📥 Baixar Modelo B Atualizado (ZIP)",
                    data=zip_bytes,
                    file_name="ModeloB-Atualizado-SemanticModel.zip",
                    mime="application/zip",
                    use_container_width=True
                )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------
# RODAPÉ
# ---------------------
st.markdown(
    '<div class="footer">Desenvolvido por Thayla Oliveira para <a href="https://sonardd.com.br" target="_blank">Sonar Data Design</a> ✨</div>',
    unsafe_allow_html=True
)


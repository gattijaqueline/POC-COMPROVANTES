from datetime import datetime
import os
from pathlib import Path
import platform
import subprocess
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(
    page_title="Localizador de Comprovantes", page_icon="📄", layout="wide"
)

st.title("📄 Localizador de Comprovantes Bancários")
st.caption(
    "Busque comprovantes na rede ou pasta local por nome, favorecido, CNPJ/CPF ou valor."
)

# ----------------- CONFIGURAÇÕES LATERAIS -----------------
with st.sidebar:
    st.header("⚙️ Configurações da Busca")

    caminho_base_padrao = r"C:\Comprovantes"
    caminho_base = st.text_input(
        "Caminho da pasta raiz:",
        value=caminho_base_padrao,
        help="Informe o caminho completo da pasta no seu computador ou na rede (ex: \\\\servidor\\financeiro\\comprovantes).",
    )

    buscar_no_conteudo = st.checkbox(
        "Ler texto dentro do PDF",
        value=True,
        help="Lê o interior dos arquivos PDF caso o nome do arquivo não coincida.",
    )

    st.markdown("---")
    sistema_atual = platform.system()
    if sistema_atual != "Windows":
        st.warning(
            "⚠️ O aplicativo está rodando em ambiente Linux/Nuvem. "
            "A visualização direta via software nativo está restrita à execução local no Windows."
        )


# ----------------- FUNÇÕES AUXILIARES -----------------
def extrair_texto_pdf(caminho_arquivo: Path) -> str:
    """Extrai o texto das páginas de um arquivo PDF."""
    try:
        reader = PdfReader(str(caminho_arquivo))
        texto_acumulado = []
        for pagina in reader.pages:
            texto = pagina.extract_text()
            if texto:
                texto_acumulado.append(texto)
        return "\n".join(texto_acumulado)
    except Exception:
        return ""


def pesquisar_arquivos(diretorio_raiz: str, termo: str, ler_conteudo: bool):
    """Percorre diretórios recursivamente procurando pelo termo informado."""
    resultados = []
    termo_limpo = termo.strip().lower()
    caminho_obj = Path(diretorio_raiz)

    if not caminho_obj.exists():
        st.error(f"O caminho informado não foi localizado: `{diretorio_raiz}`")
        return []

    for raiz, _, arquivos in os.walk(caminho_obj):
        for arquivo in arquivos:
            if arquivo.lower().endswith(".pdf"):
                caminho_completo = Path(raiz) / arquivo
                nome_arquivo = arquivo.lower()
                encontrado = False
                origem_match = ""

                # 1. Busca pelo nome do arquivo
                if termo_limpo in nome_arquivo:
                    encontrado = True
                    origem_match = "Nome do Arquivo"

                # 2. Busca pelo texto interno do PDF
                elif ler_conteudo:
                    texto_pdf = extrair_texto_pdf(caminho_completo)
                    if termo_limpo in texto_pdf.lower():
                        encontrado = True
                        origem_match = "Conteúdo do Documento"

                if encontrado:
                    try:
                        stats = caminho_completo.stat()
                        data_mod = datetime.fromtimestamp(
                            stats.st_mtime
                        ).strftime("%d/%m/%Y %H:%M")
                        tamanho_kb = round(stats.st_size / 1024, 1)
                    except Exception:
                        data_mod = "Indisponível"
                        tamanho_kb = 0.0

                    resultados.append(
                        {
                            "Arquivo": arquivo,
                            "Pasta": caminho_completo.parent.name,
                            "Caminho Completo": str(caminho_completo),
                            "Tamanho (KB)": tamanho_kb,
                            "Modificado em": data_mod,
                            "Correspondência": origem_match,
                        }
                    )

    return resultados


def abrir_arquivo_localmente(caminho_str: str):
    """Abre o arquivo no programa leitor de PDF padrão de forma multiplataforma."""
    sistema = platform.system()
    if sistema == "Windows":
        os.startfile(caminho_str)
    elif sistema == "Darwin":  # macOS
        subprocess.run(["open", caminho_str], check=False)
    else:  # Linux
        subprocess.run(["xdg-open", caminho_str], check=False)


# ----------------- CAMPO DE ENTRADA -----------------
col_busca, col_botao = st.columns([4, 1])

with col_busca:
    termo_pesquisa = st.text_input(
        "Pesquisar comprovante:",
        placeholder="Digite o nome da empresa/cliente, CNPJ, data ou valor...",
        label_visibility="collapsed",
    )

with col_botao:
    botao_buscar = st.button(
        "🔍 Buscar", use_container_width=True, type="primary"
    )

# ----------------- EXECUÇÃO DA CONSULTA -----------------
if botao_buscar and termo_pesquisa:
    with st.spinner("Pesquisando pastas e lendo comprovantes..."):
        dados = pesquisar_arquivos(
            caminho_base, termo_pesquisa, buscar_no_conteudo
        )
        st.session_state["resultados_comprovantes"] = dados

    if not dados:
        st.warning(
            f"Nenhum comprovante localizado para: **{termo_pesquisa}**"
        )
    else:
        st.success(f"Encontrado(s) **{len(dados)}** comprovante(s).")

# ----------------- EXIBIÇÃO E AÇÕES -----------------
if (
    "resultados_comprovantes" in st.session_state
    and st.session_state["resultados_comprovantes"]
):
    lista_resultados = st.session_state["resultados_comprovantes"]
    df = pd.DataFrame(lista_resultados)

    st.dataframe(
        df[
            [
                "Arquivo",
                "Pasta",
                "Correspondência",
                "Modificado em",
                "Tamanho (KB)",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 📥 Ações nos Comprovantes")

    for idx, item in enumerate(lista_resultados):
        with st.expander(
            f"📄 {item['Arquivo']} — (Pasta: {item['Pasta']})", expanded=True
        ):
            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                st.write(f"**Caminho:** `{item['Caminho Completo']}`")
                st.write(
                    f"**Correspondência:** {item['Correspondência']} | **Modificado:** {item['Modificado em']}"
                )

            with c2:
                # Leitura binária protegida para download
                try:
                    with open(item["Caminho Completo"], "rb") as f:
                        pdf_bytes = f.read()

                    st.download_button(
                        label="💾 Baixar Cópia",
                        data=pdf_bytes,
                        file_name=item["Arquivo"],
                        mime="application/pdf",
                        key=f"btn_dl_{idx}",
                        use_container_width=True,
                    )
                except Exception as erro:
                    st.error(f"Erro ao ler arquivo: {erro}")

            with c3:
                if st.button(
                    "🖨️ Abrir no Leitor",
                    key=f"btn_abrir_{idx}",
                    use_container_width=True,
                ):
                    try:
                        abrir_arquivo_localmente(item["Caminho Completo"])
                        st.toast("Comprovante enviado ao leitor!", icon="✅")
                    except Exception as erro:
                        st.error(f"Não foi possível abrir o arquivo: {erro}")

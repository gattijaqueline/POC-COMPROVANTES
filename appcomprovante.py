import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Buscador de Comprovantes", page_icon="📄", layout="wide"
)

st.title("📄 Localizador de Comprovantes Bancários")
st.caption(
    "Pesquise comprovantes na rede por nome de arquivo, cliente, CNPJ/CPF ou valor."
)

# ----------------- BARRA LATERAL (CONFIGURAÇÕES) -----------------
with st.sidebar:
    st.header("⚙️ Configurações da Busca")

    # Caminho base da rede ou pasta local onde ficam as pastas diárias
    pasta_base_padrao = r"C:\Comprovantes"  # Ajuste para a sua pasta ou caminho de rede (ex: r"\\servidor\financeiro\comprovantes")
    caminho_base = st.text_input(
        "Caminho da pasta raiz:",
        value=pasta_base_padrao,
        help="Informe o caminho completo onde ficam as pastas organizadas por dia.",
    )

    buscar_no_conteudo = st.checkbox(
        "Ler texto dentro do PDF",
        value=True,
        help="Se marcado, lê o conteúdo interno dos PDFs caso o nome do arquivo não coincida.",
    )

    st.markdown("---")
    st.info(
        "💡 **Dica:** A busca não diferencia maiúsculas de minúsculas e ignora pontuações básicas."
    )


# ----------------- FUNÇÃO DE BUSCA E LEITURA -----------------
def extrair_texto_pdf(caminho_arquivo):
    """Extrai o texto legível de todas as páginas do PDF."""
    try:
        reader = PdfReader(str(caminho_arquivo))
        texto = ""
        for pagina in reader.pages:
            texto += pagina.extract_text() or ""
        return texto
    except Exception:
        return ""


def pesquisar_arquivos(diretorio_raiz, termo, ler_conteudo):
    """Percorre todas as pastas e subpastas procurando o termo informado."""
    resultados = []
    termo_limpo = termo.strip().lower()

    if not os.path.exists(diretorio_raiz):
        st.error(f"O caminho informado não foi encontrado: `{diretorio_raiz}`")
        return []

    # Varredura recursiva por todas as subpastas
    for raiz, _, arquivos in os.walk(diretorio_raiz):
        for arquivo in arquivos:
            if arquivo.lower().endswith(".pdf"):
                caminho_completo = Path(raiz) / arquivo
                nome_arquivo = arquivo.lower()
                encontrado = False
                origem_match = ""

                # 1. Verifica no nome do arquivo
                if termo_limpo in nome_arquivo:
                    encontrado = True
                    origem_match = "Nome do Arquivo"

                # 2. Se não achou no nome e a opção estiver ativa, procura dentro do PDF
                elif ler_conteudo:
                    conteudo = extrair_texto_pdf(caminho_completo)
                    if termo_limpo in conteudo.lower():
                        encontrado = True
                        origem_match = "Conteúdo do Documento"

                if encontrado:
                    # Captura metadados do arquivo
                    stats = caminho_completo.stat()
                    data_modificacao = datetime.fromtimestamp(
                        stats.st_mtime
                    ).strftime("%d/%m/%Y %H:%M")
                    tamanho_kb = round(stats.st_size / 1024, 1)

                    resultados.append(
                        {
                            "Arquivo": arquivo,
                            "Pasta": str(caminho_completo.parent.name),
                            "Caminho Completo": str(caminho_completo),
                            "Tamanho (KB)": tamanho_kb,
                            "Modificado em": data_modificacao,
                            "Correspondência": origem_match,
                        }
                    )

    return resultados


# ----------------- CAMPO DE PESQUISA -----------------
col_busca, col_botao = st.columns([4, 1])

with col_busca:
    termo_pesquisa = st.text_input(
        "O que deseja procurar?",
        placeholder="Digite o nome do favorecido, CNPJ, data ou valor...",
        label_visibility="collapsed",
    )

with col_botao:
    botao_buscar = st.button(
        "🔍 Buscar", use_container_width=True, type="primary"
    )

# ----------------- EXECUÇÃO E EXIBIÇÃO DE RESULTADOS -----------------
if botao_buscar and termo_pesquisa:
    with st.spinner("Varrendo pastas e lendo arquivos..."):
        dados_encontrados = pesquisar_arquivos(
            caminho_base, termo_pesquisa, buscar_no_conteudo
        )

    if not dados_encontrados:
        st.warning(
            f"Nenhum comprovante encontrado com o termo: **{termo_pesquisa}**"
        )
    else:
        st.success(
            f"Foram encontrados **{len(dados_encontrados)}** comprovante(s)."
        )

        # Salva o resultado na sessão para não perder caso interaja com os botões
        st.session_state["resultados"] = dados_encontrados

if "resultados" in st.session_state and st.session_state["resultados"]:
    df = pd.DataFrame(st.session_state["resultados"])

    # Tabela resumida para visualização rápida
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

    st.markdown("### 📥 Ações nos Comprovantes Encontrados")

    # Lista individual dos arquivos encontrados com botões de ação
    for idx, item in enumerate(st.session_state["resultados"]):
        with st.expander(
            f"📄 {item['Arquivo']} — (Pasta: {item['Pasta']})", expanded=True
        ):
            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                st.write(f"**Localização:** `{item['Caminho Completo']}`")
                st.write(
                    f"**Identificado por:** {item['Correspondência']} | **Data:** {item['Modificado em']}"
                )

            with c2:
                # Botão para baixar / salvar uma cópia localmente
                with open(item["Caminho Completo"], "rb") as f:
                    pdf_bytes = f.read()

                st.download_button(
                    label="💾 Salvar Cópia",
                    data=pdf_bytes,
                    file_name=item["Arquivo"],
                    mime="application/pdf",
                    key=f"dl_{idx}",
                    use_container_width=True,
                )

            with c3:
                # Botão para abrir ou mandar para impressão no Windows
                if st.button(
                    "🖨️ Abrir / Imprimir",
                    key=f"print_{idx}",
                    use_container_width=True,
                ):
                    try:
                        # No Windows, abre o PDF no leitor padrão (onde é possível imprimir com 1 clique)
                        os.startfile(item["Caminho Completo"])
                        st.toast(
                            "Comprovante aberto no programa padrão!", icon="✅"
                        )
                    except Exception as e:
                        st.error(f"Erro ao abrir arquivo: {e}")

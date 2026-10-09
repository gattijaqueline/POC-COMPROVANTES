import os
import shutil
import subprocess
from pathlib import Path
from pypdf import PdfReader


def buscar_comprovantes(caminho_base, termo_busca, buscar_dentro_do_pdf=True):
    """Varre todas as pastas e subpastas procurando pelo termo no nome ou no conteúdo do PDF."""
    resultados = []
    termo = termo_busca.lower()

    # Percorre todas as pastas de dias/meses dentro do caminho base
    for raiz, _, arquivos in os.walk(caminho_base):
        for arquivo in arquivos:
            if arquivo.lower().endswith(".pdf"):
                caminho_completo = Path(raiz) / arquivo

                # 1. Verifica pelo nome do arquivo
                if termo in arquivo.lower():
                    resultados.append(caminho_completo)
                    continue

                # 2. Se habilitado, lê o texto dentro do PDF
                if buscar_dentro_do_pdf:
                    try:
                        reader = PdfReader(str(caminho_completo))
                        texto_completo = ""
                        for pagina in reader.pages:
                            texto_completo += (pagina.extract_text() or "").lower()

                        if termo in texto_completo:
                            resultados.append(caminho_completo)
                    except Exception:
                        # Ignora arquivos corrompidos ou que não puderam ser lidos
                        continue

    return resultados


def salvar_copia(caminho_pdf, pasta_destino):
    """Copia o comprovante encontrado para uma pasta de destino."""
    Path(pasta_destino).mkdir(parents=True, exist_ok=True)
    destino_final = Path(pasta_destino) / Path(caminho_pdf).name
    shutil.copy2(caminho_pdf, destino_final)
    print(f"Arquivo salvo com sucesso em: {destino_final}")


def abrir_ou_imprimir(caminho_pdf, imprimir_direto=False):
    """Abre o arquivo no programa padrão ou manda direto para a impressora (Windows)."""
    if imprimir_direto:
        # No Windows, aciona a ação de impressão padrão
        os.startfile(str(caminho_pdf), "print")
    else:
        # Apenas abre na tela para conferência
        os.startfile(str(caminho_pdf))

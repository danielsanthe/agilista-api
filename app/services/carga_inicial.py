
"""
Arquivo responsável pela carga inicial do AgiLista.

Cadastra as categorias padrão no banco de dados,
caso ainda não existam.
"""

from sqlmodel import Session, select

# Importa o modelo Categoria.
from app.models.categoria import Categoria


def cadastrar_categorias_padrao(session: Session):
    """
    Verifica quais categorias padrão já existem
    e cadastra somente as que ainda não existem.
    """

    # Lista com os nomes das categorias padrão.
    categorias_padrao = [
        "Hortifrúti",
        "Laticínios",
        "Padaria",
        "Limpeza",
        "Higiene Pessoal",
        "Açougue / Carnes",
        "Bebidas",
        "Mercearia / Grãos"
    ]

    # Percorre cada categoria da lista.
    for nome in categorias_padrao:

        # Verifica se já existe uma categoria padrão
        # com esse nome (usuario_id igual a None).
        consulta = select(Categoria).where(
            Categoria.nome_categoria == nome,
            Categoria.usuario_id == None
        )

        categoria_existente = session.exec(consulta).first()

        # Se não existir, prepara o cadastro.
        if categoria_existente is None:

            nova_categoria = Categoria(
                usuario_id=None,
                nome_categoria=nome,
                ativo=1,
                status_categoria="ATIVO",
                flag_sincronizado=1
            )

            session.add(nova_categoria)

    # Salva todas as categorias novas no banco.
    session.commit()

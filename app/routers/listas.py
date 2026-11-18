
"""
app/routers/listas.py

Roteador FastAPI para o gerenciamento de Listas de Compras do ÁgiLista.

Endpoints:
- GET /api/v1/listas/
- GET /api/v1/listas/{id_lista}
- POST /api/v1/listas/
- POST /api/v1/listas/com-itens
- PUT /api/v1/listas/{id_lista}
- DELETE /api/v1/listas/{id_lista}

Regras principais:
- Toda lista nasce como Planejada.
- O orçamento é obrigatório.
- O estabelecimento pode ficar vazio durante o planejamento.
- Para iniciar a compra, o nome do estabelecimento é obrigatório.
- O backend controla os timestamps de início e término.
- Listas concluídas não podem ser alteradas ou excluídas.
- A criação conjunta de lista e itens ocorre em uma única transação.
- Itens planejados não precisam estar vinculados a produtos cadastrados.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    status
)
from sqlmodel import Session, select, func

from app.database import get_session
from app.dependencies import obter_usuario_atual
from app.models.usuario import Usuario
from app.models.lista import Lista
from app.models.item_lista import ItemLista

from app.schemas.lista import (
    ListaCreate,
    ListaPlanejadaComItensCreate,
    ListaUpdate,
    ListaResponse
)


router = APIRouter(
    prefix="/api/v1/listas",
    tags=["Listas de Compras"]
)


# =====================================================================
# GET /api/v1/listas/ — LISTAR LISTAS DE COMPRAS
# =====================================================================

@router.get(
    "/",
    response_model=List[ListaResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar listas de compras do usuário",
    description=(
        "Retorna as listas de compras do usuário autenticado, "
        "com suporte a filtros por status."
    ),
    responses={
        200: {"description": "Listas retornadas com sucesso."},
        400: {"description": "Filtro de status inválido."},
        401: {"description": "Usuário não autenticado."}
    }
)
def listar_listas(
    status_filtro: Optional[str] = Query(
        default=None,
        alias="status",
        description=(
            "Filtro opcional: planejada, em_andamento, concluida, "
            "ativa (Planejada + Em Andamento) ou todas."
        )
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> List[Lista]:

    usuario_id = usuario_atual.id_usuario

    query = select(Lista).where(
        Lista.usuario_id == usuario_id
    )

    if status_filtro:
        filtro_normalizado = status_filtro.strip().lower()

        if filtro_normalizado == "planejada":
            query = query.where(
                Lista.status_lista == "Planejada"
            )

        elif filtro_normalizado in ["em_andamento", "em andamento"]:
            query = query.where(
                Lista.status_lista == "Em Andamento"
            )

        elif filtro_normalizado in ["concluida", "concluída"]:
            query = query.where(
                Lista.status_lista == "Concluída"
            )

        elif filtro_normalizado == "ativa":
            query = query.where(
                Lista.status_lista.in_(
                    ["Planejada", "Em Andamento"]
                )
            )

        elif filtro_normalizado in ["todas", "all"]:
            pass

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Filtro de status inválido: '{status_filtro}'. "
                    "Valores aceitos: planejada, em_andamento, "
                    "concluida, ativa, todas."
                )
            )

    query = query.order_by(Lista.id_lista.desc())

    return session.exec(query).all()


# =====================================================================
# GET /api/v1/listas/{id_lista} — CONSULTAR LISTA POR ID
# =====================================================================

@router.get(
    "/{id_lista}",
    response_model=ListaResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar lista de compras por ID",
    description=(
        "Retorna os detalhes de uma lista pertencente "
        "ao usuário autenticado."
    ),
    responses={
        200: {"description": "Lista encontrada."},
        401: {"description": "Usuário não autenticado."},
        404: {"description": "Lista não encontrada para o usuário."}
    }
)
def obter_lista_por_id(
    id_lista: int = Path(
        ...,
        gt=0,
        description="ID único da lista de compras."
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> Lista:

    usuario_id = usuario_atual.id_usuario

    lista = session.exec(
        select(Lista).where(
            Lista.id_lista == id_lista,
            Lista.usuario_id == usuario_id
        )
    ).first()

    if not lista:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Lista de compras com id_lista={id_lista} "
                "não foi encontrada para este usuário."
            )
        )

    return lista


# =====================================================================
# POST /api/v1/listas/ — CRIAR NOVA LISTA SEM ITENS
# =====================================================================

@router.post(
    "/",
    response_model=ListaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova lista de compras",
    description=(
        "Cria uma lista no estado Planejada. "
        "O orçamento é obrigatório, mas o estabelecimento "
        "pode ser informado somente ao iniciar a compra."
    ),
    responses={
        201: {"description": "Lista criada com sucesso."},
        401: {"description": "Usuário não autenticado."},
        409: {"description": "Já existe uma lista com esse nome."},
        500: {"description": "Erro interno ao cadastrar a lista."}
    }
)
def criar_lista(
    lista_in: ListaCreate,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> Lista:

    usuario_id = usuario_atual.id_usuario

    lista_existente = session.exec(
        select(Lista).where(
            Lista.usuario_id == usuario_id,
            func.lower(Lista.nome_lista)
            == lista_in.nome_lista.lower()
        )
    ).first()

    if lista_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Já existe uma lista cadastrada com o nome "
                f"'{lista_in.nome_lista}' para este usuário."
            )
        )

    dados_lista = lista_in.model_dump()

    timestamp_atual = datetime.now().isoformat(
        timespec="seconds"
    )

    nova_lista = Lista(
        **dados_lista,
        usuario_id=usuario_id,
        valor_total_atual=0.0,
        flag_sincronizado=1,
        data_criacao=timestamp_atual,
        data_hora_inicio=None,
        data_hora_termino=None
    )

    try:
        session.add(nova_lista)
        session.commit()
        session.refresh(nova_lista)

        return nova_lista

    except Exception:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Erro interno ao cadastrar a lista de compras no servidor."
            )
        )


# =====================================================================
# POST /api/v1/listas/com-itens — CRIAR LISTA COM SEUS ITENS
# =====================================================================

@router.post(
    "/com-itens",
    response_model=ListaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar lista planejada com seus itens",
    description=(
        "Cria uma lista planejada e todos os seus itens em uma única "
        "transação. Os itens não precisam estar vinculados a produtos "
        "cadastrados. Se algum item apresentar erro, nenhuma informação "
        "será gravada."
    ),
    responses={
        201: {"description": "Lista e itens criados com sucesso."},
        401: {"description": "Usuário não autenticado."},
        409: {"description": "Já existe uma lista com esse nome."},
        422: {"description": "Dados da lista ou dos itens inválidos."},
        500: {"description": "Erro interno ao cadastrar a lista e os itens."}
    }
)
def criar_lista_com_itens(
    lista_in: ListaPlanejadaComItensCreate,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> Lista:

    usuario_id = usuario_atual.id_usuario

    # -------------------------------------------------------------
    # 1. VERIFICAR NOME DUPLICADO
    # -------------------------------------------------------------

    lista_existente = session.exec(
        select(Lista).where(
            Lista.usuario_id == usuario_id,
            func.lower(Lista.nome_lista)
            == lista_in.nome_lista.lower()
        )
    ).first()

    if lista_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Já existe uma lista cadastrada com o nome "
                f"'{lista_in.nome_lista}' para este usuário."
            )
        )

    # -------------------------------------------------------------
    # 2. PREPARAR DADOS DA LISTA
    # -------------------------------------------------------------

    dados_lista = lista_in.model_dump(
        exclude={"itens", "status_lista"}
    )

    timestamp_atual = datetime.now().isoformat(
        timespec="seconds"
    )

    nova_lista = Lista(
        **dados_lista,
        usuario_id=usuario_id,
        status_lista="Planejada",
        valor_total_atual=0.0,
        flag_sincronizado=1,
        data_criacao=timestamp_atual,
        data_hora_inicio=None,
        data_hora_termino=None
    )

    try:
        # ---------------------------------------------------------
        # 3. INSERIR A LISTA SEM CONFIRMAR A TRANSAÇÃO
        # ---------------------------------------------------------

        session.add(nova_lista)

        # Obtém o ID gerado pelo banco para vincular os itens.
        session.flush()

        # ---------------------------------------------------------
        # 4. INSERIR TODOS OS ITENS PLANEJADOS
        # ---------------------------------------------------------

        for item_in in lista_in.itens:

            dados_item = item_in.model_dump(
                exclude={
                    "qtd_comprada",
                    "preco_unitario",
                    "flag_fora_da_lista"
                }
            )

            # O produto_id pode ser None.
            # Durante o planejamento, o usuário informa apenas
            # o nome do item, a quantidade e o preço estimado.

            novo_item = ItemLista(
                **dados_item,
                lista_id=nova_lista.id_lista,
                qtd_comprada=0.0,
                preco_unitario=0.0,
                subtotal_item=0.0,
                status_item="Pendente",
                flag_fora_da_lista=0,
                flag_sincronizado=1
            )

            session.add(novo_item)

        # ---------------------------------------------------------
        # 5. CONFIRMAR LISTA E TODOS OS ITENS DE UMA SÓ VEZ
        # ---------------------------------------------------------

        session.commit()
        session.refresh(nova_lista)

        return nova_lista

    except HTTPException:
        # Uma falha de validação também desfaz a inserção da lista.
        session.rollback()
        raise

    except Exception as e:
        session.rollback()
        print("ERRO CRIAR LISTA COM ITENS:", repr(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Erro interno ao cadastrar a lista e seus itens "
                "no servidor. Nenhum dado foi gravado."
            )
        )


# =====================================================================
# PUT /api/v1/listas/{id_lista} — ATUALIZAR LISTA
# =====================================================================

@router.put(
    "/{id_lista}",
    response_model=ListaResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar lista de compras",
    description=(
        "Permite editar listas Planejadas. Para iniciar a compra, "
        "é obrigatório informar o nome do estabelecimento. "
        "Em listas Em Andamento, permite somente concluir a compra. "
        "Listas Concluídas não podem ser alteradas."
    ),
    responses={
        200: {"description": "Lista atualizada com sucesso."},
        400: {
            "description": (
                "Estabelecimento não informado ou transição inválida."
            )
        },
        401: {"description": "Usuário não autenticado."},
        404: {"description": "Lista não encontrada."},
        409: {"description": "Conflito com as regras de negócio."},
        500: {"description": "Erro interno ao atualizar a lista."}
    }
)
def atualizar_lista(
    lista_in: ListaUpdate,
    id_lista: int = Path(
        ...,
        gt=0,
        description="ID único da lista de compras."
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> Lista:

    usuario_id = usuario_atual.id_usuario

    lista_banco = session.exec(
        select(Lista).where(
            Lista.id_lista == id_lista,
            Lista.usuario_id == usuario_id
        )
    ).first()

    if not lista_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Lista de compras com id_lista={id_lista} "
                "não foi encontrada para atualização."
            )
        )

    dados_atualizacao = lista_in.model_dump(
        exclude_unset=True
    )

    # -------------------------------------------------------------
    # PROTEÇÃO DE LISTAS EM ANDAMENTO
    # -------------------------------------------------------------

    if lista_banco.status_lista == "Em Andamento":

        if dados_atualizacao != {
            "status_lista": "Concluída"
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Uma lista com status 'Em Andamento' não pode "
                    "ter seus dados alterados. Somente a conclusão "
                    "da compra é permitida."
                )
            )

    # -------------------------------------------------------------
    # PROTEÇÃO DE LISTAS CONCLUÍDAS
    # -------------------------------------------------------------

    if lista_banco.status_lista == "Concluída":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não é possível alterar uma lista com status "
                "'Concluída'. O histórico desta compra está protegido."
            )
        )

    # -------------------------------------------------------------
    # VERIFICAÇÃO DE NOME DUPLICADO
    # -------------------------------------------------------------

    novo_nome = dados_atualizacao.get("nome_lista")

    if novo_nome and novo_nome.lower() != lista_banco.nome_lista.lower():

        nome_duplicado = session.exec(
            select(Lista).where(
                Lista.usuario_id == usuario_id,
                func.lower(Lista.nome_lista) == novo_nome.lower(),
                Lista.id_lista != id_lista
            )
        ).first()

        if nome_duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Já existe outra lista cadastrada com o nome "
                    f"'{novo_nome}' para este usuário."
                )
            )

    # -------------------------------------------------------------
    # VALIDAÇÃO DA TRANSIÇÃO DE STATUS
    # -------------------------------------------------------------

    novo_status = dados_atualizacao.get("status_lista")

    houve_alteracao = False

    if novo_status and novo_status != lista_banco.status_lista:

        status_atual = lista_banco.status_lista

        # Planejada -> Em Andamento
        if (
            status_atual == "Planejada"
            and novo_status == "Em Andamento"
        ):

            nome_estabelecimento = dados_atualizacao.get(
                "nome_estabelecimento",
                lista_banco.nome_estabelecimento
            )

            if (
                not nome_estabelecimento
                or not nome_estabelecimento.strip()
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Informe o nome do estabelecimento para "
                        "iniciar a compra."
                    )
                )

            lista_banco.data_hora_inicio = datetime.now().isoformat(
                timespec="seconds"
            )

            houve_alteracao = True

        # Em Andamento -> Concluída
        elif (
            status_atual == "Em Andamento"
            and novo_status == "Concluída"
        ):

            lista_banco.data_hora_termino = datetime.now().isoformat(
                timespec="seconds"
            )

            houve_alteracao = True

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Transição de status inválida de '{status_atual}' "
                    f"para '{novo_status}'. A sequência permitida é: "
                    "Planejada -> Em Andamento -> Concluída."
                )
            )

    # -------------------------------------------------------------
    # APLICA OS CAMPOS ENVIADOS
    # -------------------------------------------------------------

    for chave, valor in dados_atualizacao.items():

        if getattr(lista_banco, chave) != valor:
            setattr(lista_banco, chave, valor)
            houve_alteracao = True

    # -------------------------------------------------------------
    # PERSISTÊNCIA
    # -------------------------------------------------------------

    if houve_alteracao:

        lista_banco.flag_sincronizado = 1

        try:
            session.add(lista_banco)
            session.commit()
            session.refresh(lista_banco)

        except Exception:
            session.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Erro interno ao atualizar a lista de compras no servidor."
                )
            )

    return lista_banco


# =====================================================================
# DELETE /api/v1/listas/{id_lista} — EXCLUIR LISTA
# =====================================================================

@router.delete(
    "/{id_lista}",
    status_code=status.HTTP_200_OK,
    summary="Excluir lista de compras",
    description=(
        "Exclui uma lista Planejada. Os itens vinculados são "
        "excluídos automaticamente via CASCADE. "
        "Listas Em Andamento ou Concluídas não podem ser excluídas."
    ),
    responses={
        200: {"description": "Lista excluída com sucesso."},
        401: {"description": "Usuário não autenticado."},
        404: {"description": "Lista não encontrada."},
        409: {"description": "Somente listas Planejadas podem ser excluídas."},
        500: {"description": "Erro interno ao excluir a lista."}
    }
)
def excluir_lista(
    id_lista: int = Path(
        ...,
        gt=0,
        description="ID único da lista de compras."
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> dict:

    usuario_id = usuario_atual.id_usuario

    lista_banco = session.exec(
        select(Lista).where(
            Lista.id_lista == id_lista,
            Lista.usuario_id == usuario_id
        )
    ).first()

    if not lista_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Lista de compras com id_lista={id_lista} "
                "não foi encontrada para exclusão."
            )
        )

    if lista_banco.status_lista in [
        "Em Andamento",
        "Concluída"
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Não é possível excluir uma lista com status "
                f"'{lista_banco.status_lista}'. "
                "Somente listas planejadas podem ser excluídas."
            )
        )

    nome_remover = lista_banco.nome_lista

    try:
        session.delete(lista_banco)
        session.commit()

    except Exception:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Erro interno ao excluir a lista de compras no servidor."
            )
        )

    return {
        "message": (
            f"Lista '{nome_remover}' (id_lista={id_lista}) "
            "e seus itens vinculados foram excluídos com sucesso."
        )
    }

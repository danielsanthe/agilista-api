"""
app/routers/itens_lista.py

Roteador FastAPI para o gerenciamento de Itens da Lista de Compras do ÁgiLista.

Implementa regras de validação relacional por usuário, suporte a inclusão em 1 etapa
para itens fora da lista, cálculo de preço promocional e persistência transacional no SQLite.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlmodel import Session, select, func

from app.database import get_session
from app.dependencies import obter_usuario_atual
from app.models.usuario import Usuario
from app.models.lista import Lista
from app.models.item_lista import ItemLista
from app.models.produto_usuario import ProdutoUsuario
from app.schemas.item_lista import (
    ItemListaCreate,
    ItemListaUpdate,
    ItemListaResponse,
    validar_combinacao_status_origem,
    validar_promocao
)


router = APIRouter(
    prefix="/api/v1",
    tags=["Itens da Lista"]
)


# =====================================================================
# FUNÇÕES AUXILIARES DE NEGÓCIO
# =====================================================================

def _validar_propriedade_produto(session: Session, produto_id: int | None, usuario_id: int) -> None:
    """
    Valida se o produto informado existe e pertence ao catálogo pessoal do usuário autenticado.
    
    Evita associar produtos de outros usuários e aceita None (conforme regra de ON DELETE SET NULL).
    """
    if produto_id is not None:
        produto = session.exec(
            select(ProdutoUsuario).where(
                ProdutoUsuario.id_produto_usuario == produto_id,
                ProdutoUsuario.usuario_id == usuario_id
            )
        ).first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto id_produto={produto_id} não foi encontrado no seu catálogo de produtos."
            )


def _calcular_preco_e_subtotal_por_status(
    status_item: str,
    qtd_comprada: float,
    preco_unitario: float,
    flag_promocao: int,
    qtd_minima_promocional: float | None,
    preco_promocional: float | None
) -> tuple[float, float]:
    """
    Calcula o preço unitário efetivo e o subtotal do item.
    Apenas status 'Comprado' e 'Comprado FL' geram subtotal acumulado.
    
    A verificação explícita de 'is not None' garante que promoções gratuitas (R$ 0,00)
    sejam aceitas e calculadas corretamente.
    """
    # Item no estado Pendente possui subtotal zerado por regra de negócio
    if status_item == "Pendente":
        return preco_unitario or 0.0, 0.0

    preco_efetivo = preco_unitario or 0.0

    # Aplicação da regra de promoção por quantidade (F09) com checagem explícita de None
    if (
        flag_promocao == 1
        and qtd_minima_promocional is not None
        and preco_promocional is not None
    ):
        if qtd_comprada >= qtd_minima_promocional:
            preco_efetivo = preco_promocional

    subtotal = round(qtd_comprada * preco_efetivo, 2)
    return preco_efetivo, subtotal


def _recalcular_total_lista(session: Session, lista: Lista) -> None:
    """
    Soma o subtotal dos itens elegíveis ('Comprado' e 'Comprado FL')
    e atualiza o valor_total_atual na instância da Lista (sem executar commit parcial).
    """
    query_soma = select(func.sum(ItemLista.subtotal_item)).where(
        ItemLista.lista_id == lista.id_lista,
        ItemLista.status_item.in_(["Comprado", "Comprado FL"])
    )
    total_comprado = session.exec(query_soma).first() or 0.0
    lista.valor_total_atual = round(total_comprado, 2)
    lista.flag_sincronizado = 1
    session.add(lista)


# =====================================================================
# POST /api/v1/listas/{id_lista}/itens — ADICIONAR ITEM À LISTA
# =====================================================================

@router.post(
    "/listas/{id_lista}/itens",
    response_model=ItemListaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar item a uma lista de compras"
)
def criar_item_lista(
    item_in: ItemListaCreate,
    id_lista: int = Path(..., gt=0, description="ID único da lista de compras."),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> ItemLista:
    """
    Cadastra um novo item na lista do usuário.
    
    Diferencia itens planejados (POST em lista Planejada) de itens fora da lista em 1 etapa (POST em lista Em Andamento).
    Exige quantidade comprada > 0 e preço informado (>= 0) para itens fora da lista.
    """
    usuario_id = usuario_atual.id_usuario

    # 1. Busca e validação da lista pai isolada por usuário
    lista_banco = session.exec(
        select(Lista).where(
            Lista.id_lista == id_lista,
            Lista.usuario_id == usuario_id
        )
    ).first()

    if not lista_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lista de compras id_lista={id_lista} não foi encontrada para este usuário."
        )

    # 2. Bloqueios por status da lista pai
    if lista_banco.status_lista == "Concluída":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível adicionar itens a uma lista com status 'Concluída'."
        )

    dados_item = item_in.model_dump()
    flag_fora = dados_item.get("flag_fora_da_lista", 0)

    # Restrição: Lista 'Planejada' aceita apenas itens planejados; Lista 'Em Andamento' apenas itens fora da lista
    if lista_banco.status_lista == "Planejada" and flag_fora == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível adicionar itens 'fora da lista' enquanto a lista estiver com status 'Planejada'. Inicie a compra primeiro."
        )
    
    if lista_banco.status_lista == "Em Andamento" and flag_fora == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Durante uma compra 'Em Andamento', novos itens devem ser adicionados como fora da lista (flag_fora_da_lista = 1)."
        )

    # 3. Valida o pertencimento do produto_id no catálogo pessoal do usuário
    _validar_propriedade_produto(session, dados_item.get("produto_id"), usuario_id)

    # 4. Extração e validação de quantidade comprada e preço conforme a origem do item
    qtd_comprada_in = dados_item.pop("qtd_comprada", None)
    preco_unitario_in = dados_item.pop("preco_unitario", None)

    if flag_fora == 1:
        status_item = "Comprado FL"

        # Para itens fora da lista (T14), a quantidade comprada deve ser explicitamente fornecida e maior que zero
        if qtd_comprada_in is None or qtd_comprada_in <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para itens adicionados fora da lista ('flag_fora_da_lista' = 1), a 'qtd_comprada' é obrigatória e deve ser maior que 0.0."
            )
        
        # O preço unitário deve ser explicitamente fornecido (pode ser 0.0 em produtos gratuitos)
        if preco_unitario_in is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para itens adicionados fora da lista ('flag_fora_da_lista' = 1), o 'preco_unitario' é obrigatório."
            )

        qtd_comprada = qtd_comprada_in
        preco_unitario = preco_unitario_in
    else:
        status_item = "Pendente"
        qtd_comprada = 0.0
        preco_unitario = 0.0

    # 5. Cálculo do preço unitário efetivo e subtotal do item
    preco_efetivo, subtotal = _calcular_preco_e_subtotal_por_status(
        status_item=status_item,
        qtd_comprada=qtd_comprada,
        preco_unitario=preco_unitario,
        flag_promocao=dados_item.get("flag_promocao", 0),
        qtd_minima_promocional=dados_item.get("qtd_minima_promocional"),
        preco_promocional=dados_item.get("preco_promocional")
    )

    # 6. Criação do objeto ORM sem duplicação de parâmetros no construtor
    novo_item = ItemLista(
        **dados_item,
        lista_id=id_lista,
        status_item=status_item,
        qtd_comprada=qtd_comprada,
        preco_unitario=preco_efetivo,
        subtotal_item=subtotal,
        flag_sincronizado=1
    )

    try:
        # Adiciona o novo item e recalcula o valor total da lista na mesma transação
        session.add(novo_item)
        _recalcular_total_lista(session, lista_banco)
        
        # Commit transacional único
        session.commit()
        session.refresh(novo_item)

        return novo_item
    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao cadastrar o item no servidor."
        )


# =====================================================================
# GET /api/v1/listas/{id_lista}/itens — LISTAR ITENS DA LISTA
# =====================================================================

@router.get(
    "/listas/{id_lista}/itens",
    response_model=List[ItemListaResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os itens de uma lista"
)
def listar_itens_da_lista(
    id_lista: int = Path(..., gt=0, description="ID único da lista de compras."),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> List[ItemLista]:
    """Retorna os itens de uma lista isolados por usuário e ordenados por ID."""
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
            detail=f"Lista de compras id_lista={id_lista} não foi encontrada para este usuário."
        )

    itens = session.exec(
        select(ItemLista)
        .where(ItemLista.lista_id == id_lista)
        .order_by(ItemLista.id_item_lista.asc())
    ).all()

    return itens


# =====================================================================
# PUT /api/v1/itens-lista/{id_item} — ATUALIZAR ITEM DA LISTA
# =====================================================================

@router.put(
    "/itens-lista/{id_item}",
    response_model=ItemListaResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar dados de um item da lista"
)
def atualizar_item_lista(
    item_in: ItemListaUpdate,
    id_item: int = Path(..., gt=0, description="ID único do item da lista."),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> ItemLista:
    """
    Atualiza parcialmente um item da lista.
    
    Aplica validação de promoção e regras de origem sobre o estado mesclado,
    bloqueia a marcação como 'Comprado' em listas 'Planejada', exige quantidade comprada > 0
    para itens comprados e reseta métricas ao voltar para 'Pendente'.
    """
    usuario_id = usuario_atual.id_usuario

    # 1. Busca o item garantindo a propriedade da lista pai pelo usuário
    query = (
        select(ItemLista)
        .join(Lista, ItemLista.lista_id == Lista.id_lista)
        .where(
            ItemLista.id_item_lista == id_item,
            Lista.usuario_id == usuario_id
        )
    )
    item_banco = session.exec(query).first()

    if not item_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item id_item={id_item} não foi encontrado para este usuário."
        )

    lista_banco = session.exec(
        select(Lista).where(Lista.id_lista == item_banco.lista_id)
    ).first()

    # 2. Bloqueio de alteração em listas concluídas
    if lista_banco and lista_banco.status_lista == "Concluída":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível alterar itens de uma lista com status 'Concluída'."
        )

    # 3. Extrai apenas os campos explicitamente enviados no payload
    dados_atualizacao = item_in.model_dump(exclude_unset=True)

    # 4. Trava de alteração de dados do planejamento durante a compra 'Em Andamento'
    if lista_banco and lista_banco.status_lista == "Em Andamento":
        campos_planejamento_bloqueados = ["nome_item_planejado", "qtd_planejada", "preco_estimado"]
        for campo in campos_planejamento_bloqueados:
            if campo in dados_atualizacao:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O campo '{campo}' do planejamento não pode ser alterado enquanto a compra estiver 'Em Andamento'."
                )

    # 5. Imutabilidade da Origem (flag_fora_da_lista)
    if "flag_fora_da_lista" in dados_atualizacao:
        if dados_atualizacao["flag_fora_da_lista"] != item_banco.flag_fora_da_lista:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A origem do item ('flag_fora_da_lista') é imutável e não pode ser alterada após a criação."
            )

    # 6. Validação de pertencimento do produto se informado
    if "produto_id" in dados_atualizacao and dados_atualizacao["produto_id"] is not None:
        _validar_propriedade_produto(session, dados_atualizacao["produto_id"], usuario_id)

    # 7. Aplicação das alterações sobre a instância ORM (Estado Mesclado)
    for chave, valor in dados_atualizacao.items():
        setattr(item_banco, chave, valor)

    # 8. Trava de status por estado da lista: proíbe marcar como 'Comprado' ou 'Comprado FL' se a lista for 'Planejada'
    if lista_banco and lista_banco.status_lista == "Planejada":
        if item_banco.status_item in ["Comprado", "Comprado FL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível marcar um item como 'Comprado' enquanto a lista estiver 'Planejada'. Inicie a compra primeiro."
            )

    # 9. Validação da Combinação Final de Status x Origem
    try:
        validar_combinacao_status_origem(item_banco.status_item, item_banco.flag_fora_da_lista)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err)
        )

    # 10. Validação de quantidade comprada obrigatória para itens comprados no estado mesclado
    if item_banco.status_item in ["Comprado", "Comprado FL"]:
        if item_banco.qtd_comprada is None or item_banco.qtd_comprada <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Para marcar ou manter o item como 'Comprado' ou 'Comprado FL', a 'qtd_comprada' deve ser maior que 0.0."
            )

    # 11. Validação da Promoção no Estado Mesclado (válida para qualquer status do item)
    if item_banco.flag_promocao == 1:
        try:
            validar_promocao(
                flag_promocao=item_banco.flag_promocao,
                qtd_minima_promocional=item_banco.qtd_minima_promocional,
                preco_promocional=item_banco.preco_promocional
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err)
            )
    else:
        item_banco.qtd_minima_promocional = None
        item_banco.preco_promocional = None

    # 12. Regra de Negócio: Se o status for revertido para 'Pendente', reseta as métricas de compra
    if item_banco.status_item == "Pendente":
        item_banco.qtd_comprada = 0.0
        item_banco.preco_unitario = 0.0
        item_banco.subtotal_item = 0.0
    else:
        # 13. Recalcula preço unitário efetivo e subtotal para itens comprados
        preco_efetivo, subtotal = _calcular_preco_e_subtotal_por_status(
            status_item=item_banco.status_item,
            qtd_comprada=item_banco.qtd_comprada or 0.0,
            preco_unitario=item_banco.preco_unitario or 0.0,
            flag_promocao=item_banco.flag_promocao,
            qtd_minima_promocional=item_banco.qtd_minima_promocional,
            preco_promocional=item_banco.preco_promocional
        )
        item_banco.preco_unitario = preco_efetivo
        item_banco.subtotal_item = subtotal

    item_banco.flag_sincronizado = 1

    try:
        # Persistência transacional única
        session.add(item_banco)
        if lista_banco:
            _recalcular_total_lista(session, lista_banco)
            
        session.commit()
        session.refresh(item_banco)

        return item_banco

    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar o item no servidor."
        )


# =====================================================================
# DELETE /api/v1/itens-lista/{id_item} — EXCLUIR ITEM DA LISTA
# =====================================================================

@router.delete(
    "/itens-lista/{id_item}",
    status_code=status.HTTP_200_OK,
    summary="Remover item de uma lista de compras"
)
def excluir_item_lista(
    id_item: int = Path(..., gt=0, description="ID único do item da lista."),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    session: Session = Depends(get_session)
) -> dict:
    """
    Exclui permanentemente um item da lista.
    
    Impede a remoção de itens em listas 'Concluída' e bloqueia a exclusão de itens planejados durante compras 'Em Andamento'.
    Utiliza session.flush() antes do recálculo para garantir que o SELECT SUM reflita a exclusão.
    """
    usuario_id = usuario_atual.id_usuario

    # 1. Busca o item isolado por usuário
    query = (
        select(ItemLista)
        .join(Lista, ItemLista.lista_id == Lista.id_lista)
        .where(
            ItemLista.id_item_lista == id_item,
            Lista.usuario_id == usuario_id
        )
    )
    item_banco = session.exec(query).first()

    if not item_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item id_item={id_item} não foi encontrado para exclusão."
        )

    lista_banco = session.exec(
        select(Lista).where(Lista.id_lista == item_banco.lista_id)
    ).first()

    # 2. Bloqueios por status da lista pai
    if lista_banco:
        if lista_banco.status_lista == "Concluída":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não é possível remover itens de uma lista com status 'Concluída'."
            )

        # Proteção do planejamento durante compras 'Em Andamento'
        if lista_banco.status_lista == "Em Andamento" and item_banco.flag_fora_da_lista == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Itens planejados não podem ser excluídos durante a compra. Altere o status para 'Pendente'."
            )

    nome_remover = item_banco.nome_item_planejado

    try:
        # Marca o item para exclusão e descarrega a exclusão para o banco de dados (flush)
        session.delete(item_banco)
        session.flush()

        # Recalcula o valor total da lista considerando o banco atualizado
        if lista_banco:
            _recalcular_total_lista(session, lista_banco)

        session.commit()

        return {
            "message": f"Item '{nome_remover}' (id_item={id_item}) foi removido da lista com sucesso."
        }

    except Exception:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao excluir o item no servidor."
        )
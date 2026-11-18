"""
app/models/item_lista.py

Modelo relacional e de dados (SQLModel/ORM) para os Itens da Lista de Compras do ÁgiLista.

Esta classe representa tanto o planejamento inicial de compras feito pelo usuário 
quanto a execução e auditoria em tempo real no supermercado (preços pagos, quantidades
compradas, regras de promoção de atacado e itens avulsos adicionados durante a compra).

Possui suporte nativo à arquitetura Offline-First (sincronização cloud) e histórico imutável.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class ItemLista(SQLModel, table=True):
    """
    Entidade mapeada para a tabela 'itens_lista' no banco de dados SQLite e PostgreSQL.
    
    Gerencia o ciclo de vida completo do item:
    - Planejamento (estimativa de preços e quantidades).
    - Execução da compra (subtotais reais, preços unitários e promoções por volume).
    - Preservação do histórico em caso de exclusão de produtos do catálogo pessoal.
    """

    # Define explicitamente o nome da tabela no banco de dados relacional.
    __tablename__ = "itens_lista"

    # =========================================================================
    # IDENTIFICAÇÃO E CONTROLE DE SINCRONIZAÇÃO (OFFLINE-FIRST)
    # =========================================================================

    # Identificador único e chave primária do item gerado localmente ou no servidor.
    id_item_lista: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Chave primária autoincrementável do item da lista."
    )

    # Identificador correspondente no banco de dados da nuvem para reconciliação de sync.
    servidor_id: Optional[int] = Field(
        default=None,
        description="ID do registro correspondente no servidor PostgreSQL remoto (Sync)."
    )

    # Flag que indica se as alterações locais deste registro já foram enviadas à API.
    # 0 = Pendente de envio para o servidor | 1 = Totalmente sincronizado
    flag_sincronizado: int = Field(
        default=1,
        description="Indica o estado de sincronização offline-first (0 = Pendente, 1 = Sincronizado)."
    )

    # =========================================================================
    # RELACIONAMENTOS E CHAVES ESTRANGEIRAS (FOREIGN KEYS)
    # =========================================================================

    # Chave estrangeira que vincula obrigatoriamente o item a uma Lista de Compras pai.
    # O argumento 'ondelete="CASCADE"' garante que, se a lista for excluída, todos os
    # seus itens associados serão removidos automaticamente do banco.
    lista_id: int = Field(
        foreign_key="listas.id_lista",
        index=True,
        ondelete="CASCADE",
        description="Chave estrangeira vinculando o item à lista de compras pai."
    )

    # Chave estrangeira opcional vinculando o item a um produto do catálogo do usuário.
    # Pode ser NULL caso seja um item textual livre ou se o produto for excluído.
    # O argumento 'ondelete="SET NULL"' garante a proteção histórica do item: se o produto
    # for removido do catálogo, o item da compra permanece no banco com produto_id = NULL.
    produto_id: Optional[int] = Field(
        default=None,
        foreign_key="produtos_usuario.id_produto_usuario",
        ondelete="SET NULL",
        description="Chave estrangeira opcional para o catálogo de produtos (ON DELETE SET NULL)."
    )

    # =========================================================================
    # DADOS DE PLANEJAMENTO DO ITEM (FASE PREPARATÓRIA)
    # =========================================================================

    # Nome descritivo do item planejado pelo usuário. Preservado permanentemente,
    # mesmo se a referência do produto no catálogo for desvinculada.
    nome_item_planejado: str = Field(
        max_length=200,
        description="Nome do item conforme digitado ou importado no planejamento."
    )

    # Quantidade que o usuário pretende comprar inicialmente.
    qtd_planejada: float = Field(
        default=1.0,
        description="Quantidade estimada para compra (padrão: 1.0)."
    )

    # Preço unitário estimado para fins de projeção do orçamento total da lista.
    preco_estimado: float = Field(
        default=0.0,
        description="Preço unitário estimado antes da ida ao estabelecimento."
    )

    # =========================================================================
    # DADOS EFETIVOS DA COMPRA (FASE DE EXECUÇÃO NO ESTABELECIMENTO)
    # =========================================================================

    # Quantidade efetivamente pega e colocada no carrinho durante a compra real.
    qtd_comprada: Optional[float] = Field(
        default=0.0,
        description="Quantidade real verificada e colocada no carrinho."
    )

    # Preço unitário efetivamente praticado na gôndola/caixa do supermercado.
    preco_unitario: Optional[float] = Field(
        default=0.0,
        description="Preço unitário real pago pelo produto."
    )

    # Subtotal calculado do item: (qtd_comprada x preco_unitario efetivo).
    # Este valor é somado para compor o 'valor_total_atual' da lista de compras.
    subtotal_item: Optional[float] = Field(
        default=0.0,
        description="Subtotal calculado em moeda local (qtd_comprada * preco_unitario)."
    )

    # =========================================================================
    # REGRAS DE NEGÓCIO PARA PROMOÇÕES (ATACAREJO / DESCONTO POR VOLUME)
    # =========================================================================

    # Flag indicando se o item está elegível a uma regra de preço promocional/atacado.
    # 0 = Sem promoção atrelada | 1 = Possui regra de promoção ativa
    flag_promocao: int = Field(
        default=0,
        description="Sinaliza a presença de oferta promocional por quantidade (0 = Não, 1 = Sim)."
    )

    # Quantidade mínima no carrinho exigida para aplicar a precificação de atacado.
    qtd_minima_promocional: Optional[float] = Field(
        default=None,
        description="Quantidade limite a partir da qual o preço promocional é acionado."
    )

    # Preço promocional por unidade aplicado quando a quantidade mínima for atingida.
    preco_promocional: Optional[float] = Field(
        default=None,
        description="Preço unitário especial praticado mediante alcance da quantidade mínima."
    )

    # =========================================================================
    # SITUAÇÃO E ORIGEM DO ITEM DENTRO DA LISTA
    # =========================================================================

    # Estado atual do item na jornada de compra.
    # Valores aceitos: 'PENDENTE', 'COMPRADO', 'NAO_ENCONTRADO' ou 'CANCELADO'.
    status_item: str = Field(
        default="PENDENTE",
        max_length=30,
        description="Status do item na lista (PENDENTE, COMPRADO, NAO_ENCONTRADO, CANCELADO)."
    )

    # Flag indicando se o item foi adicionado impulsivamente/avulso no meio da compra,
    # ou seja, sem que tivesse sido planejado antes de ir ao supermercado.
    # 0 = Item planejado em casa | 1 = Item inserido diretamente durante a compra
    flag_fora_da_lista: int = Field(
        default=0,
        description="Indica se o item foi adicionado 'na hora' durante a compra (0 = Não, 1 = Sim)."
    )
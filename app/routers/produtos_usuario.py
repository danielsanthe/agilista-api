"""
app/routers/produtos_usuario.py

Roteador da API responsável pelo gerenciamento do catálogo particular de produtos do usuário.

Fornece endpoints para o CRUD completo de produtos do usuário autenticado:
- GET    /api/v1/produtos/                  : Lista todos os produtos do usuário
- GET    /api/v1/produtos/{id_produto_usuario} : Consulta detalhes de um produto
- POST   /api/v1/produtos/                  : Cadastra um novo produto pessoal
- PUT    /api/v1/produtos/{id_produto_usuario} : Atualiza parcialmente um produto
- DELETE /api/v1/produtos/{id_produto_usuario} : Remove um produto do catálogo pessoal

Regras de Negócio e Segurança:
1. Isolamento Absoluto: O usuário só enxerga, edita e remove seus próprios produtos (usuario_id).
2. Validação de Categoria Ativa: Garante que a categoria exista, esteja ATIVA (ativo=1) e pertença ao escopo permitido.
3. Validação de Catálogo Global: Checa a existência do produto global caso o ID seja fornecido.
4. Conflito de Nomes: Impede duplicidade no cadastro e edição (ignorando o próprio ID no PUT).
5. Otimização de Escrita: Compara alterações reais no PUT e evita escritas e alteração de flag se os valores forem idênticos.
6. Proteção de Histórico (DELETE): Bloqueia a remoção de produtos vinculados a itens de listas com HTTP 409 e rollback seguro.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, or_

# Importações de dependências de sessão do banco e autenticação
from app.database import get_session
from app.dependencies import obter_usuario_atual

# Importações de modelos ORM
from app.models.produto_usuario import ProdutoUsuario
from app.models.categoria import Categoria
from app.models.usuario import Usuario
from app.models.produto_global import ProdutoGlobal

# Importações dos DTOs de validação Pydantic v2
from app.schemas.produto_usuario import (
    ProdutoUsuarioCreate,
    ProdutoUsuarioUpdate,
    ProdutoUsuarioResponse
)

# Declaração do roteador para o módulo de produtos do usuário
router = APIRouter(
    prefix="/api/v1/produtos",
    tags=["Produtos do Usuário"]
)


# =====================================================================
# FUNÇÕES AUXILIARES DE VALIDAÇÃO INTERNA
# =====================================================================

def _validar_categoria_existente(
    categoria_id: int,
    usuario_id: int,
    session: Session
) -> Categoria:
    """
    Verifica se a categoria informada existe, está ATIVA (ativo = 1) e acessível ao usuário.
    Uma categoria é válida se for global (usuario_id IS NULL) ou se pertencer ao próprio usuário.

    :param categoria_id: ID da categoria a ser validada.
    :param usuario_id: ID do usuário autenticado.
    :param session: Sessão ativa do banco de dados.
    :return: Instância da Categoria localizada.
    :raises HTTPException 404: Se a categoria não for encontrada, estiver inativa ou pertencer a outro usuário.
    """
    statement = select(Categoria).where(
        Categoria.id_categoria == categoria_id,
        Categoria.ativo == 1,
        or_(
            Categoria.usuario_id == usuario_id,
            Categoria.usuario_id.is_(None)
        )
    )
    categoria = session.exec(statement).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"A categoria com id_categoria={categoria_id} não existe, está inativa ou não está disponível para este usuário."
        )

    return categoria


def _validar_produto_global(
    produto_global_id: Optional[int],
    session: Session
) -> None:
    """
    Verifica se o produto global informado existe no catálogo base do servidor.
    A associação é opcional. Se produto_global_id for None, a validação é ignorada.

    :param produto_global_id: Identificador opcional do catálogo global.
    :param session: Sessão ativa do banco de dados.
    :raises HTTPException 404: Se o produto global não for encontrado.
    """
    if produto_global_id is None:
        return

    produto_global = session.get(ProdutoGlobal, produto_global_id)
    if not produto_global:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto global com id_produto_global={produto_global_id} não foi encontrado."
        )


def _verificar_duplicidade_nome_produto(
    nome_produto: str,
    usuario_id: int,
    session: Session,
    id_produto_ignorar: Optional[int] = None
) -> None:
    """
    Garante a unicidade do nome do produto no catálogo do usuário (case-insensitive).

    :param nome_produto: Nome do produto a ser checado.
    :param usuario_id: ID do usuário autenticado.
    :param session: Sessão ativa do banco de dados.
    :param id_produto_ignorar: ID do próprio produto durante atualização (PUT) para desconsiderá-lo.
    :raises HTTPException 409: Se já existir outro produto com esse mesmo nome no catálogo.
    """
    statement = select(ProdutoUsuario).where(
        ProdutoUsuario.usuario_id == usuario_id,
        ProdutoUsuario.nome_produto.ilike(nome_produto)
    )

    # No caso de atualização (PUT), ignora o registro que está sendo alterado
    if id_produto_ignorar is not None:
        statement = statement.where(ProdutoUsuario.id_produto_usuario != id_produto_ignorar)

    produto_existente = session.exec(statement).first()

    if produto_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um produto cadastrado com o nome '{nome_produto}' no seu catálogo."
        )


# =====================================================================
# ENDPOINT 1: LISTAR PRODUTOS DO USUÁRIO
# =====================================================================

@router.get(
    "/",
    response_model=List[ProdutoUsuarioResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar produtos do usuário",
    description="Retorna os produtos cadastrados no catálogo pessoal do usuário autenticado."
)
def listar_produtos(
    categoria_id: Optional[int] = Query(
        default=None,
        gt=0,
        description="Filtro opcional por categoria."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> List[ProdutoUsuario]:
    """
    Lista os produtos pertencentes ao usuário autenticado.
    Permite filtrar os resultados por categoria e ordena alfabeticamente pelo nome.
    """
    # 1. Consulta base: restringe os resultados ao usuário autenticado.
    statement = select(ProdutoUsuario).where(
        ProdutoUsuario.usuario_id == usuario_atual.id_usuario
    )

    # 2. Aplica o filtro por categoria, quando informado.
    if categoria_id is not None:
        statement = statement.where(
            ProdutoUsuario.categoria_id == categoria_id
        )

    # 3. Ordena os produtos alfabeticamente.
    statement = statement.order_by(
        ProdutoUsuario.nome_produto.asc()
    )

    # 4. Executa a consulta e recupera os registros.
    produtos = session.exec(statement).all()

    # 5. Retorna os produtos encontrados.
    return produtos


# =====================================================================
# ENDPOINT 2: CONSULTAR PRODUTO POR ID
# =====================================================================

@router.get(
    "/{id_produto_usuario}",
    response_model=ProdutoUsuarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar produto por ID",
    description="Retorna os detalhes de um produto específico do catálogo do usuário autenticado.",
    responses={
        404: {"description": "Produto não encontrado."},
        422: {"description": "Parâmetro de ID inválido."}
    }
)
def buscar_produto_por_id(
    id_produto_usuario: int = Path(
        ...,
        gt=0,
        description="Identificador único do produto do usuário."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoUsuario:
    """
    Recupera um produto específico através de seu ID.
    Aplica validação de ID positivo e isolamento por usuário (404 Not Found se pertencer a outro).
    """
    # 1. Consulta o produto filtrando por ID e proprietário
    statement = select(ProdutoUsuario).where(
        ProdutoUsuario.id_produto_usuario == id_produto_usuario,
        ProdutoUsuario.usuario_id == usuario_atual.id_usuario
    )

    produto = session.exec(statement).first()

    # 2. Se o produto não for localizado ou pertencer a outro usuário, lança exceção 404
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com id_produto_usuario={id_produto_usuario} não foi encontrado."
        )

    # 3. Retorna o produto localizado
    return produto


# =====================================================================
# ENDPOINT 3: CADASTRAR NOVO PRODUTO
# =====================================================================

@router.post(
    "/",
    response_model=ProdutoUsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo produto",
    description="Cria um novo produto personalizado no catálogo do usuário autenticado.",
    responses={
        201: {"description": "Produto cadastrado com sucesso."},
        404: {"description": "Categoria ou Produto Global não encontrado/inativo."},
        409: {"description": "Conflito de duplicidade de nome ou erro de integridade."}
    }
)
def criar_produto(
    produto_in: ProdutoUsuarioCreate,
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoUsuario:
    """
    Insere um novo produto no catálogo do usuário.
    Valida a existência e status ativo da categoria, validação de produto global e bloqueio de duplicidade de nome.
    """
    # 1. Valida se a categoria informada existe, está ativa e disponível no escopo do usuário
    _validar_categoria_existente(
        categoria_id=produto_in.categoria_id,
        usuario_id=usuario_atual.id_usuario,
        session=session
    )

    # 2. Valida se o produto global informado existe no catálogo base (se fornecido)
    _validar_produto_global(
        produto_global_id=produto_in.produto_global_id,
        session=session
    )

    # 3. Idempotência para sincronização mobile: se já existir produto com mesmo nome, retorna-o
    produto_existente = session.exec(
        select(ProdutoUsuario).where(
            ProdutoUsuario.usuario_id == usuario_atual.id_usuario,
            ProdutoUsuario.nome_produto.ilike(produto_in.nome_produto.strip()),
        )
    ).first()
    if produto_existente:
        return produto_existente

    # 4. Instancia o modelo ORM injetando o usuario_id do token e sinaliza sincronização
    novo_produto = ProdutoUsuario(
        **produto_in.model_dump(),
        usuario_id=usuario_atual.id_usuario,
        flag_sincronizado=1
    )

    # 5. Persiste no banco com tratamento de exceção transacional 409 Conflict
    try:
        session.add(novo_produto)
        session.commit()
        session.refresh(novo_produto)
        return novo_produto
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível cadastrar o produto devido a um conflito com os dados existentes."
        )


# =====================================================================
# ENDPOINT 4: ATUALIZAR PRODUTO (PARCIAL)
# =====================================================================

@router.put(
    "/{id_produto_usuario}",
    response_model=ProdutoUsuarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar produto",
    description="Atualiza parcialmente as informações de um produto existente do usuário autenticado.",
    responses={
        200: {"description": "Produto atualizado com sucesso (ou mantido sem alterações)."},
        404: {"description": "Produto, Categoria ou Produto Global não encontrado."},
        409: {"description": "Conflito de duplicidade de nome ou erro de integridade."},
        422: {"description": "Parâmetro de ID ou payload inválido."}
    }
)
def atualizar_produto(
    produto_in: ProdutoUsuarioUpdate,
    id_produto_usuario: int = Path(
        ...,
        gt=0,
        description="Identificador único do produto a ser atualizado."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoUsuario:
    """
    Atualiza apenas os campos enviados no JSON (utiliza exclude_unset=True).
    Filtra alterações reais para evitar re-gravações desnecessárias e preserva flag_sincronizado se nada mudar.
    Revalida categoria ativa, produto global e duplicidade de nome apenas para os campos alterados.
    """
    # 1. Busca o produto garantindo pertencimento ao usuário logado
    statement = select(ProdutoUsuario).where(
        ProdutoUsuario.id_produto_usuario == id_produto_usuario,
        ProdutoUsuario.usuario_id == usuario_atual.id_usuario
    )
    produto_db = session.exec(statement).first()

    if not produto_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com id_produto_usuario={id_produto_usuario} não foi encontrado para atualização."
        )

    # 2. Extrai apenas os campos fornecidos explicitamente na requisição
    dados_atualizacao = produto_in.model_dump(exclude_unset=True)

    # 3. Otimização: remove campos cujos valores enviados são idênticos aos já armazenados
    dados_atualizacao = {
        campo: valor
        for campo, valor in dados_atualizacao.items()
        if getattr(produto_db, campo) != valor
    }

    # Se nenhum valor mudou efetivamente, retorna o registro intacto sem nova operação de escrita
    if not dados_atualizacao:
        return produto_db

    # 4. Se a categoria estiver sendo alterada, valida se existe e está ativa
    if "categoria_id" in dados_atualizacao:
        _validar_categoria_existente(
            categoria_id=dados_atualizacao["categoria_id"],
            usuario_id=usuario_atual.id_usuario,
            session=session
        )

    # 5. Se produto_global_id for enviado, valida sua existência no catálogo (aceita null para desvincular)
    if "produto_global_id" in dados_atualizacao:
        _validar_produto_global(
            produto_global_id=dados_atualizacao["produto_global_id"],
            session=session
        )

    # 6. Se o nome estiver sendo alterado, valida duplicidade ignorando o próprio produto
    if "nome_produto" in dados_atualizacao:
        _verificar_duplicidade_nome_produto(
            nome_produto=dados_atualizacao["nome_produto"],
            usuario_id=usuario_atual.id_usuario,
            session=session,
            id_produto_ignorar=id_produto_usuario
        )

    # 7. Aplica as alterações reais no objeto carregado do ORM
    for campo, valor in dados_atualizacao.items():
        setattr(produto_db, campo, valor)

    # Sinaliza necessidade de sincronização mobile apenas quando houve mudança real
    produto_db.flag_sincronizado = 1

    # 8. Salva as modificações com rollback transacional em caso de erro de integridade
    try:
        session.add(produto_db)
        session.commit()
        session.refresh(produto_db)
        return produto_db
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o produto devido a um conflito com as restrições do banco de dados."
        )


# =====================================================================
# ENDPOINT 5: EXCLUIR PRODUTO
# =====================================================================

@router.delete(
    "/{id_produto_usuario}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir produto",
    description="Remove um produto do catálogo pessoal do usuário autenticado, desde que não esteja associado a itens de listas.",
    responses={
        204: {"description": "Produto excluído com sucesso."},
        404: {"description": "Produto não encontrado."},
        409: {"description": "Produto vinculado a histórico em listas de compras."},
        422: {"description": "Parâmetro de ID inválido."}
    }
)
def excluir_produto(
    id_produto_usuario: int = Path(
        ...,
        gt=0,
        description="Identificador único do produto a ser excluído."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> None:
    """
    Exclui permanentemente um produto do catálogo do usuário.
    Garante o isolamento por proprietário e Impede a exclusão se houver qualquer vínculo em itens de listas de compras (integridade referencial).
    """
    # 1. Localiza o produto confirmando o pertencimento ao usuário logado
    statement = select(ProdutoUsuario).where(
        ProdutoUsuario.id_produto_usuario == id_produto_usuario,
        ProdutoUsuario.usuario_id == usuario_atual.id_usuario
    )
    produto = session.exec(statement).first()

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com id_produto_usuario={id_produto_usuario} não foi encontrado para exclusão."
        )

    # 2. Executa a deleção com proteção transacional contra violações de integridade referencial
    try:
        session.delete(produto)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir este produto porque ele está vinculado a itens de listas de compras e possui histórico associado."
        )
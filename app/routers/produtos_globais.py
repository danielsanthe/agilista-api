
"""
app/routers/produtos_globais.py

Rotas da API para gerenciamento do Catálogo Global de Produtos
do AgiLista.

O catálogo global armazena informações compartilhadas entre
todos os usuários do aplicativo.

Responsabilidades:
- Consultar produtos globais.
- Pesquisar produtos pelo código de barras.
- Cadastrar novos produtos globais.
- Atualizar produtos existentes.
- Excluir produtos globais sem vínculos pessoais.
- Validar a associação com categorias padrão ativas.
- Restringir operações de escrita aos administradores.

Regras de negócio:
- Produtos globais devem possuir código de barras único.
- Todo produto global deve estar associado a uma categoria padrão.
- A categoria associada deve estar ativa.
- Categorias personalizadas de usuários não podem ser utilizadas.
- Produtos globais vinculados a produtos pessoais não podem ser excluídos.
- Somente administradores podem cadastrar, atualizar ou excluir produtos.
"""

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status
)

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session

from app.dependencies import (
    obter_usuario_atual,
    obter_admin_atual
)

from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.produto_global import ProdutoGlobal
from app.models.produto_usuario import ProdutoUsuario

from app.schemas.produto_global import (
    ProdutoGlobalCreate,
    ProdutoGlobalUpdate,
    ProdutoGlobalResponse,
    ProdutoGlobalPaginadoResponse,
    CategoriaGlobalResumoResponse
)


# =====================================================================
# SEÇÃO 1: CONFIGURAÇÃO DO ROUTER
# =====================================================================

router = APIRouter(
    prefix="/api/v1/produtos-globais",
    tags=["Produtos Globais"]
)


# =====================================================================
# SEÇÃO 2: FUNÇÕES AUXILIARES
# =====================================================================

# ---------------------------------------------------------------------
# 2.1. Validar categoria padrão
# ---------------------------------------------------------------------

def _validar_categoria_padrao(
    categoria_id: int,
    session: Session
) -> Categoria:
    """
    Verifica se a categoria informada pode ser utilizada
    no catálogo global.

    Regras:
    - A categoria deve existir.
    - Deve estar ativa.
    - Deve ser uma categoria padrão do sistema.
    - Categorias personalizadas de usuários não são permitidas.
    """

    categoria = session.exec(
        select(Categoria).where(
            Categoria.id_categoria == categoria_id,
            Categoria.usuario_id.is_(None),
            Categoria.ativo == 1
        )
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Categoria inválida. Informe uma categoria padrão "
                "existente e ativa no sistema."
            )
        )

    return categoria


# ---------------------------------------------------------------------
# 2.2. Verificar duplicidade do código de barras
# ---------------------------------------------------------------------

def _verificar_duplicidade_codigo_barras(
    codigo_barras: str,
    session: Session,
    produto_id: Optional[int] = None
) -> None:
    """
    Verifica se o código de barras já está cadastrado
    em outro produto global.

    O parâmetro produto_id permite ignorar o próprio produto
    durante uma atualização.
    """

    consulta = select(ProdutoGlobal).where(
        ProdutoGlobal.codigo_barras == codigo_barras
    )

    # Durante uma atualização, ignora o próprio produto.
    if produto_id is not None:
        consulta = consulta.where(
            ProdutoGlobal.id_produto_global != produto_id
        )

    produto_existente = session.exec(consulta).first()

    if produto_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Já existe um produto global com esse código de barras."
            )
        )


# ---------------------------------------------------------------------
# 2.3. Montar resposta do produto global
# ---------------------------------------------------------------------

def _montar_resposta_produto_global(
    produto: ProdutoGlobal,
    categoria: Categoria
) -> ProdutoGlobalResponse:
    """
    Monta a resposta do produto global incluindo os dados resumidos
    da categoria associada.

    O relacionamento é montado explicitamente porque o modelo
    ProdutoGlobal não possui relacionamento ORM chamado categoria.
    """

    return ProdutoGlobalResponse(
        id_produto_global=produto.id_produto_global,
        codigo_barras=produto.codigo_barras,
        nome_oficial=produto.nome_oficial,
        unidade_medida_padrao=produto.unidade_medida_padrao,
        categoria_id=produto.categoria_id,
        categoria=CategoriaGlobalResumoResponse(
            id_categoria=categoria.id_categoria,
            nome_categoria=categoria.nome_categoria
        )
    )


# ---------------------------------------------------------------------
# 2.4. Buscar produto global pelo identificador
# ---------------------------------------------------------------------

def _buscar_produto_global(
    produto_id: int,
    session: Session
) -> ProdutoGlobal:
    """
    Localiza um produto global pelo identificador.

    Retorna HTTP 404 quando o produto não existir.
    """

    produto = session.get(
        ProdutoGlobal,
        produto_id
    )

    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto global não encontrado."
        )

    return produto


# ---------------------------------------------------------------------
# 2.5. Buscar categoria associada ao produto
# ---------------------------------------------------------------------

def _buscar_categoria_produto(
    produto: ProdutoGlobal,
    session: Session
) -> Categoria:
    """
    Localiza a categoria associada ao produto global.

    Retorna HTTP 500 caso a categoria não seja encontrada,
    pois isso representa uma inconsistência nos dados do banco.
    """

    categoria = session.get(
        Categoria,
        produto.categoria_id
    )

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "A categoria associada ao produto não foi encontrada."
            )
        )

    return categoria


# =====================================================================
# SEÇÃO 3: CONSULTAR PRODUTOS GLOBAIS COM FILTROS (GET)
# =====================================================================

@router.get(
    "/",
    response_model=List[ProdutoGlobalResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar produtos globais",
    description=(
        "Retorna os produtos cadastrados no catálogo global. "
        "Permite filtrar por categoria e pesquisar pelo nome oficial."
    ),
    responses={
        200: {
            "description": "Lista de produtos globais retornada."
        },
        400: {
            "description": "Categoria informada inválida."
        },
        401: {
            "description": "Usuário não autenticado."
        },
        422: {
            "description": "Parâmetros de pesquisa inválidos."
        }
    }
)
def listar_produtos_globais(
    categoria_id: Optional[int] = Query(
        default=None,
        gt=0,
        description="Filtra os produtos pelo identificador da categoria."
    ),
    descricao: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Pesquisa parte do nome oficial do produto."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> List[ProdutoGlobalResponse]:
    """
    Retorna os produtos cadastrados no catálogo global.

    Filtros opcionais:
    - categoria_id: identifica a categoria desejada.
    - descricao: pesquisa parte do nome oficial.

    Os dois filtros podem ser utilizados simultaneamente.

    A operação exige usuário autenticado.
    """

    # Inicia a consulta de produtos globais.
    consulta = select(ProdutoGlobal)

    # Aplica o filtro por categoria, quando informado.
    if categoria_id is not None:

        # Garante que a categoria seja padrão e esteja ativa.
        _validar_categoria_padrao(
            categoria_id,
            session
        )

        consulta = consulta.where(
            ProdutoGlobal.categoria_id == categoria_id
        )

    # Aplica o filtro por parte da descrição, quando informado.
    if descricao is not None:

        # Remove espaços desnecessários no início e no final.
        descricao = descricao.strip()

        # Não permite pesquisa contendo somente espaços.
        if not descricao:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "O filtro de descrição não pode conter "
                    "apenas espaços."
                )
            )

        # Pesquisa o texto em qualquer posição do nome.
        consulta = consulta.where(
            ProdutoGlobal.nome_oficial.ilike(
                f"%{descricao}%"
            )
        )

    # Ordena os resultados pelo nome oficial.
    consulta = consulta.order_by(
        ProdutoGlobal.nome_oficial
    )

    # Executa a consulta no banco de dados.
    produtos = session.exec(consulta).all()

    # Prepara a lista de respostas com os dados das categorias.
    respostas: List[ProdutoGlobalResponse] = []

    for produto in produtos:

        # Recupera a categoria associada ao produto.
        categoria = _buscar_categoria_produto(
            produto,
            session
        )

        # Monta a resposta incluindo os dados da categoria.
        respostas.append(
            _montar_resposta_produto_global(
                produto,
                categoria
            )
        )

    return respostas

# =====================================================================
# SEÇÃO 3.1: CONSULTAR PRODUTOS GLOBAIS PAGINADOS (GET /paginado)
# =====================================================================

@router.get(
    "/paginado",
    response_model=ProdutoGlobalPaginadoResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar produtos globais com busca e paginação",
    description=(
        "Retorna uma página de produtos do catálogo global com contagem total. "
        "Permite filtrar simultaneamente por nome oficial, código de barras e categoria."
    ),
    responses={
        200: {"description": "Página de produtos globais retornada."},
        400: {"description": "Categoria informada inválida."},
        401: {"description": "Usuário não autenticado."},
    }
)
def listar_produtos_globais_paginado(
    busca: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Busca por parte do nome oficial ou código de barras (EAN)."
    ),
    categoria_id: Optional[int] = Query(
        default=None,
        gt=0,
        description="Filtra os produtos pelo identificador da categoria."
    ),
    limit: int = Query(
        default=25,
        ge=1,
        le=200,
        description="Quantidade de itens por página."
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Deslocamento inicial da paginação."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoGlobalPaginadoResponse:
    """
    Consulta escalável para grandes volumes (ex: 1 milhão de produtos).
    Executa COUNT(*) e LIMIT/OFFSET diretamente no banco de dados.
    """

    # Lista de condições dinâmicas (WHERE)
    condicoes = []

    # 1. Filtro por Categoria Padrão
    if categoria_id is not None:
        _validar_categoria_padrao(categoria_id, session)
        condicoes.append(ProdutoGlobal.categoria_id == categoria_id)

    # 2. Filtro combinado por Nome Oficial ou Código de Barras (EAN)
    if busca is not None and busca.strip():
        termo = busca.strip()
        condicoes.append(
            or_(
                ProdutoGlobal.nome_oficial.ilike(f"%{termo}%"),
                ProdutoGlobal.codigo_barras.ilike(f"%{termo}%")
            )
        )

    # Calcula o total de registros correspondentes no banco (COUNT)
    consulta_total = select(func.count(ProdutoGlobal.id_produto_global))
    if condicoes:
        consulta_total = consulta_total.where(*condicoes)
    total_registros = session.exec(consulta_total).one()

    # Busca apenas a fatia (LIMIT/OFFSET) da página atual
    consulta_itens = select(ProdutoGlobal)
    if condicoes:
        consulta_itens = consulta_itens.where(*condicoes)

    consulta_itens = (
        consulta_itens
        .order_by(ProdutoGlobal.nome_oficial.asc())
        .offset(offset)
        .limit(limit)
    )

    produtos = session.exec(consulta_itens).all()

    # Carrega o mapa de categorias em uma única consulta (evita N+1 queries)
    categorias_map = {
        cat.id_categoria: cat
        for cat in session.exec(select(Categoria)).all()
    }

    itens_resposta: List[ProdutoGlobalResponse] = []
    for produto in produtos:
        categoria = categorias_map.get(produto.categoria_id)
        if not categoria:
            categoria = _buscar_categoria_produto(produto, session)
        itens_resposta.append(
            _montar_resposta_produto_global(produto, categoria)
        )

    return ProdutoGlobalPaginadoResponse(
        total=total_registros,
        limit=limit,
        offset=offset,
        itens=itens_resposta
    )


# =====================================================================
# SEÇÃO 4: CONSULTAR PRODUTO POR CÓDIGO DE BARRAS (GET)
# =====================================================================

@router.get(
    "/codigo-barras/{codigo_barras}",
    response_model=ProdutoGlobalResponse,
    status_code=status.HTTP_200_OK,
    summary="Buscar produto pelo código de barras",
    description=(
        "Localiza um produto global pelo código de barras. "
        "Endpoint utilizado pelo aplicativo após a leitura do produto."
    ),
    responses={
        200: {
            "description": "Produto global encontrado."
        },
        401: {
            "description": "Usuário não autenticado."
        },
        404: {
            "description": "Produto não encontrado no catálogo global."
        },
        422: {
            "description": "Código de barras inválido."
        }
    }
)
def buscar_por_codigo_barras(
    codigo_barras: str = Path(
        ...,
        min_length=1,
        max_length=50,
        description="Código de barras do produto."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoGlobalResponse:
    """
    Localiza um produto global pelo código de barras.

    Este endpoint será utilizado pelo aplicativo mobile após
    a leitura do código de barras pela câmera do celular.

    Retorna:
    - Código de barras.
    - Nome oficial.
    - Unidade de medida.
    - Categoria padrão.

    A operação exige usuário autenticado.
    """

    # Pesquisa o produto pelo código de barras.
    produto = session.exec(
        select(ProdutoGlobal).where(
            ProdutoGlobal.codigo_barras == codigo_barras
        )
    ).first()

    # Verifica se o produto foi encontrado.
    if not produto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado no catálogo global."
        )

    # Recupera a categoria associada ao produto.
    categoria = _buscar_categoria_produto(
        produto,
        session
    )

    # Retorna o produto com os dados da categoria.
    return _montar_resposta_produto_global(
        produto,
        categoria
    )


# =====================================================================
# SEÇÃO 5: CONSULTAR PRODUTO POR IDENTIFICADOR (GET)
# =====================================================================

@router.get(
    "/{id_produto_global}",
    response_model=ProdutoGlobalResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar produto global por ID",
    description=(
        "Consulta os dados de um produto global pelo identificador "
        "registrado no servidor."
    ),
    responses={
        200: {
            "description": "Produto global encontrado."
        },
        401: {
            "description": "Usuário não autenticado."
        },
        404: {
            "description": "Produto global não encontrado."
        },
        422: {
            "description": "Identificador inválido."
        }
    }
)
def consultar_produto_global(
    id_produto_global: int = Path(
        ...,
        gt=0,
        description="Identificador do produto global no servidor."
    ),
    session: Session = Depends(get_session),
    usuario_atual: Usuario = Depends(obter_usuario_atual)
) -> ProdutoGlobalResponse:
    """
    Consulta um produto global pelo identificador.

    A operação exige usuário autenticado.
    """

    # Localiza o produto pelo identificador.
    produto = _buscar_produto_global(
        id_produto_global,
        session
    )

    # Recupera a categoria associada ao produto.
    categoria = _buscar_categoria_produto(
        produto,
        session
    )

    # Retorna o produto com os dados da categoria.
    return _montar_resposta_produto_global(
        produto,
        categoria
    )


# =====================================================================
# SEÇÃO 6: CADASTRAR PRODUTO GLOBAL (POST)
# =====================================================================

@router.post(
    "/",
    response_model=ProdutoGlobalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar produto global",
    description=(
        "Cadastra um novo produto no catálogo global. "
        "Operação restrita aos administradores."
    ),
    responses={
        201: {
            "description": "Produto global cadastrado com sucesso."
        },
        400: {
            "description": "Categoria padrão inválida ou inativa."
        },
        403: {
            "description": "Operação permitida somente para administradores."
        },
        409: {
            "description": "Código de barras já cadastrado ou conflito de dados."
        },
        422: {
            "description": "Dados enviados inválidos."
        }
    }
)
def cadastrar_produto_global(
    dados: ProdutoGlobalCreate,
    session: Session = Depends(get_session),
    administrador: Usuario = Depends(obter_admin_atual)
) -> ProdutoGlobalResponse:
    """
    Cadastra um novo produto no catálogo global.

    A operação é permitida somente para administradores.

    Antes do cadastro:
    - Verifica se o código de barras já existe.
    - Verifica se a categoria padrão existe e está ativa.
    """

    # Verifica se o código de barras já está cadastrado.
    _verificar_duplicidade_codigo_barras(
        dados.codigo_barras,
        session
    )

    # Valida a categoria padrão informada.
    categoria = _validar_categoria_padrao(
        dados.categoria_id,
        session
    )

    # Cria o objeto do produto global.
    produto = ProdutoGlobal(
        codigo_barras=dados.codigo_barras,
        nome_oficial=dados.nome_oficial,
        unidade_medida_padrao=dados.unidade_medida_padrao,
        categoria_id=categoria.id_categoria
    )

    try:

        # Adiciona o produto à sessão.
        session.add(produto)

        # Persiste o cadastro no banco de dados.
        session.commit()

        # Atualiza o objeto com o identificador gerado.
        session.refresh(produto)

    except IntegrityError:

        # Desfaz a transação em caso de conflito no banco.
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não foi possível cadastrar o produto. "
                "Verifique os dados."
            )
        )

    # Retorna o produto cadastrado com os dados da categoria.
    return _montar_resposta_produto_global(
        produto,
        categoria
    )


# =====================================================================
# SEÇÃO 7: ATUALIZAR PRODUTO GLOBAL (PUT)
# =====================================================================

@router.put(
    "/{id_produto_global}",
    response_model=ProdutoGlobalResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar produto global",
    description=(
        "Atualiza os dados de um produto global existente. "
        "Somente os campos enviados serão considerados."
    ),
    responses={
        200: {
            "description": "Produto global atualizado com sucesso."
        },
        400: {
            "description": "Categoria padrão inválida ou inativa."
        },
        403: {
            "description": "Operação permitida somente para administradores."
        },
        404: {
            "description": "Produto global não encontrado."
        },
        409: {
            "description": "Código de barras duplicado ou conflito de dados."
        },
        422: {
            "description": "Dados enviados inválidos."
        }
    }
)
def atualizar_produto_global(
    id_produto_global: int = Path(
        ...,
        gt=0,
        description="Identificador do produto global no servidor."
    ),
    dados: ProdutoGlobalUpdate = ...,
    session: Session = Depends(get_session),
    administrador: Usuario = Depends(obter_admin_atual)
) -> ProdutoGlobalResponse:
    """
    Atualiza os dados de um produto global existente.

    A operação é permitida somente para administradores.

    Somente os campos enviados na requisição serão atualizados.
    """

    # Localiza o produto que será atualizado.
    produto = _buscar_produto_global(
        id_produto_global,
        session
    )

    # Obtém somente os campos enviados na requisição.
    dados_atualizacao = dados.model_dump(
        exclude_unset=True
    )

    # Identifica somente os campos que realmente mudaram.
    dados_alterados = {
        campo: valor
        for campo, valor in dados_atualizacao.items()
        if getattr(produto, campo) != valor
    }

    # Se nenhum valor mudou, retorna o cadastro atual.
    if not dados_alterados:

        categoria = _buscar_categoria_produto(
            produto,
            session
        )

        return _montar_resposta_produto_global(
            produto,
            categoria
        )

    # Verifica duplicidade caso o código de barras seja alterado.
    if "codigo_barras" in dados_alterados:

        _verificar_duplicidade_codigo_barras(
            dados_alterados["codigo_barras"],
            session,
            produto_id=id_produto_global
        )

    # Valida a categoria caso ela seja alterada.
    if "categoria_id" in dados_alterados:

        categoria = _validar_categoria_padrao(
            dados_alterados["categoria_id"],
            session
        )

    else:

        # Mantém a categoria atualmente associada ao produto.
        categoria = _buscar_categoria_produto(
            produto,
            session
        )

    # Aplica somente os campos que realmente foram alterados.
    for campo, valor in dados_alterados.items():
        setattr(produto, campo, valor)

    try:

        # Adiciona o produto atualizado à sessão.
        session.add(produto)

        # Persiste as alterações no banco de dados.
        session.commit()

        # Atualiza o objeto com os dados persistidos.
        session.refresh(produto)

    except IntegrityError:

        # Desfaz a transação em caso de conflito no banco.
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o produto global."
        )

    # Retorna o produto atualizado com os dados da categoria.
    return _montar_resposta_produto_global(
        produto,
        categoria
    )


# =====================================================================
# SEÇÃO 8: EXCLUIR PRODUTO GLOBAL (DELETE)
# =====================================================================

@router.delete(
    "/{id_produto_global}",
    status_code=status.HTTP_200_OK,
    summary="Excluir produto global",
    description=(
        "Exclui um produto global do catálogo, desde que não existam "
        "produtos pessoais vinculados a ele. Operação restrita aos "
        "administradores."
    ),
    responses={
        200: {
            "description": "Produto global excluído com sucesso."
        },
        403: {
            "description": "Operação permitida somente para administradores."
        },
        404: {
            "description": "Produto global não encontrado."
        },
        409: {
            "description": "Existem produtos pessoais vinculados ao produto global."
        },
        422: {
            "description": "Identificador inválido."
        }
    }
)
def excluir_produto_global(
    id_produto_global: int = Path(
        ...,
        gt=0,
        description="Identificador do produto global no servidor."
    ),
    session: Session = Depends(get_session),
    administrador: Usuario = Depends(obter_admin_atual)
):
    """
    Exclui um produto global do catálogo.

    A operação é permitida somente para administradores.

    A exclusão será bloqueada caso existam produtos pessoais
    vinculados ao produto global.

    Essa proteção preserva a integridade dos cadastros dos usuários.
    """

    # Localiza o produto que será excluído.
    produto = _buscar_produto_global(
        id_produto_global,
        session
    )

    # Verifica se algum produto pessoal utiliza este produto global.
    produto_vinculado = session.exec(
        select(ProdutoUsuario).where(
            ProdutoUsuario.produto_global_id == id_produto_global
        )
    ).first()

    # Impede a exclusão quando existem vínculos pessoais.
    if produto_vinculado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Não é possível excluir este produto global, "
                "pois existem produtos de usuários vinculados a ele."
            )
        )

    try:

        # Remove o produto global.
        session.delete(produto)

        # Confirma a exclusão no banco de dados.
        session.commit()

    except IntegrityError:

        # Desfaz a transação em caso de conflito no banco.
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível excluir o produto global."
        )

    # Retorna a confirmação da exclusão.
    return {
        "mensagem": "Produto global excluído com sucesso.",
        "id_produto_global": id_produto_global
    }

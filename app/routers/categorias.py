"""
=============================================================================
AGILISTA API — ROTEADOR DE CATEGORIAS (APIROUTER)
=============================================================================

Este arquivo implementa o controle de rotas HTTP para o recurso de Categorias.

Responsabilidades Principais:
1. Listar categorias globais (padrão) e personalizadas do usuário autenticado.
2. Permitir o cadastro de novas categorias personalizadas.
3. Consultar os detalhes de uma categoria por ID com proteção de privacidade.
4. Atualizar somente categorias personalizadas criadas pelo próprio usuário (com checagem de duplicidade).
5. Excluir categorias personalizadas sem produtos associados (com tratamento de IntegrityError).

Regras de Segurança de Dados:
- Categorias Padrão (usuario_id = NULL) são globais e estritamente SOMENTE LEITURA.
- Operações de modificação em categorias padrão retornam HTTP 403 Forbidden.
- O usuário não pode acessar, modificar ou excluir categorias de outros usuários.
"""

# Importa Annotated para injeção de dependências tipadas do FastAPI.
from typing import Annotated, Literal, Optional

# Importa utilitários do FastAPI para criação do roteador, injeção de dependências, tratamento de erros e query params.
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Importa Session do SQLModel para lidar com transações no banco, além das funções de consulta (select e or_).
from sqlmodel import Session, select, or_

# Importa a exceção de integridade do SQLAlchemy para tratar falhas em exclusões atômicas.
from sqlalchemy.exc import IntegrityError

# Importa o gerador de sessão do banco de dados (get_session).
from app.database import get_session

# Importa a dependência de usuário autenticado.
from app.dependencies import obter_usuario_atual

# Importa os modelos de banco de dados necessários para consultas e validações de relacionamento.
from app.models.usuario import Usuario
from app.models.categoria import Categoria
from app.models.produto_usuario import ProdutoUsuario

# Importa os DTOs (Schemas Pydantic) para validação de entrada e formatação de saída.
from app.schemas.categoria import (
    CategoriaCriarSchema,
    CategoriaAtualizarSchema,
    CategoriaRespostaSchema,
)


# =====================================================================
# CONCEITO: APIRouter (Modularização de Rotas)
# Agrupa os endpoints sob a tag 'Categorias' e define o prefixo '/api/v1/categorias'.
# =====================================================================
router = APIRouter(
    prefix="/api/v1/categorias",
    tags=["Categorias"]
)


# =====================================================================
# 1. LISTAR CATEGORIAS (GET /api/v1/categorias/)
# =====================================================================
@router.get(
    "/",
    response_model=list[CategoriaRespostaSchema],
    status_code=status.HTTP_200_OK,
    summary="Listar categorias disponíveis",
    description=(
        "Retorna as categorias padrão do sistema e as categorias "
        "personalizadas pertencentes ao usuário autenticado. "
        "Permite filtrar as categorias ativas, inativas e todas."
    ),
    responses={
        200: {
            "description": "Categorias disponíveis retornadas com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        422: {
            "description": "Parâmetro de consulta inválido. Informe ATIVO ou INATIVO em status_categoria."
        }
    }
    
)
def listar_categorias(
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session),
    status_categoria: Optional[Literal["ATIVO", "INATIVO"]] = Query(
        default=None,
        description="Filtra as categorias por situação: ATIVO ou INATIVO. Se não informado, retorna todas."
    ),
):
    """
    Retorna as categorias padrão do sistema (usuario_id = NULL) 
    juntamente com as categorias personalizadas do usuário autenticado.
    """
    # Extrai o ID do usuário injetado pela dependência de autenticação
    id_usr = usuario_atual.id_usuario

    # Constrói a consulta SQL: Busca categorias padrão (usuario_id IS NULL) OU do usuário logado
    consulta = select(Categoria).where(
        or_(
            Categoria.usuario_id == None,
            Categoria.usuario_id == id_usr
        )
    )

    # Aplica o filtro condicional para retornar apenas ativas se o parâmetro for passado como True
    if status_categoria is not None:
        consulta = consulta.where(
            Categoria.status_categoria == status_categoria
        )

    # Ordena alfabeticamente pelo nome para apresentação legível na interface móvel
    consulta = consulta.order_by(Categoria.nome_categoria.asc())
    
    # Executa a busca no banco de dados SQLite/Postgres
    categorias = sessao.exec(consulta).all()
    
    # Retorna a lista serializada conforme o CategoriaRespostaSchema
    return categorias


# =====================================================================
# 2. CONSULTAR CATEGORIA POR ID (GET /api/v1/categorias/{id_categoria})
# =====================================================================
@router.get(
    "/{id_categoria}",
    response_model=CategoriaRespostaSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar categoria por ID",
    description=(
        "Busca uma categoria pelo seu identificador. "
        "Permite consultar categorias padrão do sistema e categorias "
        "personalizadas pertencentes ao usuário autenticado."
    ),
    responses={
        200: {
            "description": "Categoria localizada e retornada com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        404: {
            "description": "Categoria não encontrada ou pertencente a outro usuário."
        },
        422: {
            "description": "Identificador da categoria inválido."
        }
    }
)
def obter_categoria_por_id(
    id_categoria: int,
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session),
):
    """
    Busca e retorna uma categoria específica pelo seu identificador (ID).
    Retorna 404 Not Found caso a categoria não exista ou pertença a outro usuário.
    """
    # Identifica o ID do usuário logado
    id_usr = usuario_atual.id_usuario

    # Busca a categoria pela chave primária
    categoria = sessao.get(Categoria, id_categoria)

    # Regra de Privacidade e Isolamento:
    # Se a categoria não existir OU se for uma categoria personalizada pertencente a outro usuário, lança 404 Not Found
    if not categoria or (categoria.usuario_id is not None and categoria.usuario_id != id_usr):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria não localizada com id={id_categoria}."
        )

    # Retorna os detalhes da categoria validada
    return categoria


# =====================================================================
# 3. CADASTRAR CATEGORIA PERSONALIZADA (POST /api/v1/categorias/)
# =====================================================================
@router.post(
    "/",
    response_model=CategoriaRespostaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar categoria personalizada",
    description=(
        "Cria uma nova categoria personalizada vinculada ao usuário autenticado. "
        "O identificador do proprietário é definido automaticamente pelo backend. "
        "Não permite cadastrar categorias com nomes já utilizados nas categorias "
        "padrão ou nas categorias personalizadas do próprio usuário."
    ),
    responses={
        201: {
            "description": "Categoria personalizada cadastrada com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        409: {
            "description": "Já existe uma categoria com o mesmo nome no escopo do usuário."
        },
        422: {
            "description": "Dados inválidos para o cadastro da categoria. Verifique os campos enviados."
        }
    }
)
def criar_categoria(
    dados: CategoriaCriarSchema,
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session),
):
    """
    Cadastra uma nova categoria personalizada vinculada ao usuário autenticado.
    O backend atribui o usuario_id automaticamente, impedindo criação de globais pelo app.
    """
    # Associa a nova categoria ao ID do usuário autenticado
    id_usr = usuario_atual.id_usuario

    # Checagem de duplicação: Verifica se o nome já é usado em categorias padrão ou do próprio usuário
    categoria_existente = sessao.exec(
        select(Categoria).where(
            Categoria.nome_categoria == dados.nome_categoria,
            or_(Categoria.usuario_id == None, Categoria.usuario_id == id_usr)
        )
    ).first()

    # Se houver conflito de nomes no mesmo escopo, retorna HTTP 409 Conflict
    if categoria_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma categoria cadastrada com o nome '{dados.nome_categoria}'."
        )

    # Instancia o novo registro com o usuario_id injetado pelo backend
    nova_categoria = Categoria(
        usuario_id=id_usr,
        nome_categoria=dados.nome_categoria,
        ativo=dados.ativo,
        status_categoria=dados.status_categoria,
        flag_sincronizado=1
    )

    # Persiste o novo registro no banco de dados de forma segura
    sessao.add(nova_categoria)
    sessao.commit()
    sessao.refresh(nova_categoria)
    
    # Retorna a categoria recém-criada com status HTTP 201 Created
    return nova_categoria


# =====================================================================
# 4. ATUALIZAR CATEGORIA (PUT /api/v1/categorias/{id_categoria})
# =====================================================================
@router.put(
    "/{id_categoria}",
    response_model=CategoriaRespostaSchema,
    status_code=status.HTTP_200_OK,
    summary="Atualizar categoria personalizada",
    description=(
        "Atualiza os dados de uma categoria personalizada pertencente ao usuário autenticado. "
        "Permite alterar somente os campos enviados na requisição. "
        "Categorias padrão do sistema são somente leitura e não podem ser modificadas. "
        "Também verifica a existência de nomes duplicados."
    ),
    responses={
        200: {
            "description": "Categoria personalizada atualizada com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        403: {
            "description": "Operação proibida. As categorias padrão do sistema são somente leitura."
        },
        404: {
            "description": "Categoria não encontrada ou pertencente a outro usuário."
        },
        409: {
            "description": "Conflito de nome. Já existe outra categoria com o nome informado."
        },
        422: {
            "description": "Identificador ou dados enviados para atualização inválidos."
        }
    }
)
def atualizar_categoria(
    id_categoria: int,
    dados: CategoriaAtualizarSchema,
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session),
):
    """
    Atualiza os dados de uma categoria personalizada pertencente ao usuário.
    Tentativas de alterar categorias padrão do sistema (usuario_id = NULL) retornam 403.
    Verifica conflito de nome duplicado antes de persistir.
    """
    # Identifica o proprietário da requisição
    id_usr = usuario_atual.id_usuario

    # Busca a categoria a ser atualizada no banco
    categoria_banco = sessao.get(Categoria, id_categoria)

    # Se não encontrar o registro, lana 404
    if not categoria_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria não localizada com id={id_categoria}."
        )

    # REGRA DE SEGURANÇA 1: Bloqueia edições em categorias padrão globais do sistema (usuario_id IS NULL)
    if categoria_banco.usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="As categorias padrão do sistema são somente leitura e não podem ser alteradas."
        )

    # REGRA DE SEGURANÇA 2: Bloqueia edições em categorias personalizadas de outros usuários
    if categoria_banco.usuario_id != id_usr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria não localizada com id={id_categoria}."
        )

    # Extrai do schema apenas os campos explicitamente informados na requisição
    dados_atualizados = dados.model_dump(exclude_unset=True)

    # CHECAGEM DE DUPLICIDADE: Se o nome for alterado, garante que não colida com outra categoria existente
    if "nome_categoria" in dados_atualizados:
        novo_nome = dados_atualizados["nome_categoria"]
        categoria_existente = sessao.exec(
            select(Categoria).where(
                Categoria.nome_categoria == novo_nome,
                Categoria.id_categoria != id_categoria, # Exclui a própria categoria da verificação
                or_(Categoria.usuario_id == None, Categoria.usuario_id == id_usr)
            )
        ).first()

        # Bloqueia caso o novo nome pertença a outra categoria acessível
        if categoria_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe outra categoria cadastrada com o nome '{novo_nome}'."
            )

    # Atualiza dinamicamente os atributos da categoria recuperada do banco
    for campo, valor in dados_atualizados.items():
        setattr(categoria_banco, campo, valor)

    # Efetiva as alterações na base de dados
    sessao.add(categoria_banco)
    sessao.commit()
    sessao.refresh(categoria_banco)
    
    # Retorna o registro atualizado
    return categoria_banco


# =====================================================================
# 5. EXCLUIR CATEGORIA (DELETE /api/v1/categorias/{id_categoria})
# =====================================================================
@router.delete(
    "/{id_categoria}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover categoria personalizada",
    description=(
        "Remove permanentemente uma categoria personalizada pertencente ao usuário autenticado, "
        "desde que não existam produtos vinculados. "
        "As categorias padrão do sistema não podem ser excluídas."
    ),
    responses={
        204: {
            "description": "Categoria removida com sucesso. A resposta não possui conteúdo."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        403: {
            "description": "Operação proibida. As categorias padrão do sistema não podem ser excluídas."
        },
        404: {
            "description": "Categoria não encontrada ou pertencente a outro usuário."
        },
        409: {
            "description": "Não foi possível excluir a categoria porque existem produtos ou outros registros vinculados."
        },
        422: {
            "description": "Identificador da categoria inválido."
        }
    }
)
def remover_categoria(
    id_categoria: int,
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session),
):
    """
    Remove uma categoria personalizada do usuário, desde que ela não possua produtos vinculados.
    Categorias padrão retornam 403. Se houver produtos vinculados, lança 409 Conflict.
    Trata exceções de integridade do banco (IntegrityError) com rollback.
    """
    # Identifica o usuário requisitante
    id_usr = usuario_atual.id_usuario

    # Localiza o registro no banco
    categoria_banco = sessao.get(Categoria, id_categoria)

    # Se não existir, lança 404 Not Found
    if not categoria_banco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria não localizada com id={id_categoria}."
        )

    # REGRA DE SEGURANÇA 1: Protege as 8 categorias padrão do sistema contra exclusão
    if categoria_banco.usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="As categorias padrão do sistema são somente leitura e não podem ser excluídas."
        )

    # REGRA DE SEGURANÇA 2: Impede exclusão de categorias pertencentes a terceiros
    if categoria_banco.usuario_id != id_usr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoria não localizada com id={id_categoria}."
        )

    # REGRA DE INTEGRIDADE (ON DELETE RESTRICT): Verifica se há produtos cadastrados vinculados a esta categoria
    produto_vinculado = sessao.exec(
        select(ProdutoUsuario).where(ProdutoUsuario.categoria_id == id_categoria)
    ).first()

    # Se houver produtos dependentes, bloqueia a remoção com HTTP 409 Conflict
    if produto_vinculado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir esta categoria, pois existem produtos vinculados a ela."
        )

    # Tenta remover o registro do banco dentro de um bloco protegido contra falhas de chave estrangeira
    try:
        sessao.delete(categoria_banco)
        sessao.commit()
    except IntegrityError:
        # Se ocorrer violação atômica de integridade, faz o rollback da transação e avisa o cliente
        sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir esta categoria, pois existem registros vinculados a ela no banco."
        )

    # Respostas de exclusão bem-sucedidas (204 No Content) não retornam corpo de JSON
    return None
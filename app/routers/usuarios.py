"""
=============================================================================
AGILISTA API — ROTEADOR DE USUÁRIOS (APIROUTER)
=============================================================================

Este arquivo implementa o controle de rotas HTTP para o recurso de Usuários.

Responsabilidades Principais:
1. Consultar os dados do perfil do usuário autenticado (/me).
2. Permitir que o usuário atualize suas próprias informações de perfil.
3. Permitir que administradores listem e gerenciem os clientes cadastrados.
4. Tratar acessos não autorizados e manter a privacidade dos dados.

Regras de Segurança de Dados:
- Senhas brutas nunca são retornadas em endpoints de leitura.
- A listagem geral de usuários é estritamente restrita ao perfil ADMIN.
- Usuários comuns apenas leem e modificam seus próprios cadastros.
"""

from typing import Annotated, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.dependencies import obter_usuario_atual, obter_admin_atual
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioCriarSchema,
    UsuarioAtualizarSchema,
    UsuarioRespostaSchema,
)
from app.security import obter_hash_senha


# =====================================================================
# CONCEITO: APIRouter (Modularização de Rotas)
# Agrupa os endpoints sob a tag 'Usuários' e define o prefixo '/api/v1/usuarios'.
# =====================================================================
router = APIRouter(
    prefix="/api/v1/usuarios",
    tags=["Usuários"]
)


# =====================================================================
# 1. CONSULTAR PERFIL DO USUÁRIO AUTENTICADO (GET /api/v1/usuarios/me)
# =====================================================================
@router.get(
    "/me",
    response_model=UsuarioRespostaSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar dados do usuário autenticado",
    description=(
        "Retorna as informações cadastrais e de perfil do usuário "
        "associado ao token JWT informado na requisição."
    ),
    responses={
        200: {
            "description": "Perfil do usuário retornado com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        }
    }
)
def obter_perfil_usuario_atual(
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)]
):
    """
    Retorna os detalhes cadastrais do próprio usuário autenticado.
    """
    return usuario_atual


# =====================================================================
# 2. ATUALIZAR PERFIL DO USUÁRIO AUTENTICADO (PUT /api/v1/usuarios/me)
# =====================================================================
@router.put(
    "/me",
    response_model=UsuarioRespostaSchema,
    status_code=status.HTTP_200_OK,
    summary="Atualizar dados do próprio perfil",
    description=(
        "Permite que o usuário autenticado atualize seus próprios "
        "dados cadastrais, endereço e senha de acesso."
    ),
    responses={
        200: {
            "description": "Perfil atualizado com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        409: {
            "description": "Conflito de e-mail ou CPF já utilizado por outro usuário."
        },
        422: {
            "description": "Dados enviados inválidos. Verifique os campos fornecidos."
        }
    }
)
def atualizar_perfil_usuario_atual(
    dados: UsuarioAtualizarSchema,
    usuario_atual: Annotated[Usuario, Depends(obter_usuario_atual)],
    sessao: Session = Depends(get_session)
):
    """
    Atualiza parcialmente os campos cadastrais do próprio usuário autenticado.
    """
    dados_atualizados = dados.model_dump(exclude_unset=True)

    # Trata a atualização de senha convertendo para hash
    if "senha" in dados_atualizados:
        senha_plana = dados_atualizados.pop("senha")
        dados_atualizados["senha_hash"] = obter_hash_senha(senha_plana)

    # Checagem de duplicação de E-mail caso tenha sido alterado
    if "email" in dados_atualizados and dados_atualizados["email"] != usuario_atual.email:
        email_existente = sessao.exec(
            select(Usuario).where(
                Usuario.email == dados_atualizados["email"],
                Usuario.id_usuario != usuario_atual.id_usuario
            )
        ).first()

        if email_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"O e-mail '{dados_atualizados['email']}' já está em uso por outro usuário."
            )

    # Aplica as alterações dinamicamente no objeto do usuário logado
    for campo, valor in dados_atualizados.items():
        setattr(usuario_atual, campo, valor)

    try:
        sessao.add(usuario_atual)
        sessao.commit()
        sessao.refresh(usuario_atual)
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o perfil devido a um conflito de dados (ex: CPF ou e-mail duplicado)."
        )

    return usuario_atual


# =====================================================================
# 3. LISTAR TODOS OS USUÁRIOS (GET /api/v1/usuarios/) — ADMIN
# =====================================================================
@router.get(
    "/",
    response_model=list[UsuarioRespostaSchema],
    status_code=status.HTTP_200_OK,
    summary="Listar todos os usuários (Administrador)",
    description=(
        "Retorna a lista completa de clientes e usuários cadastrados no sistema. "
        "Esta operação é restrita exclusivamente a administradores."
    ),
    responses={
        200: {
            "description": "Lista de usuários retornada com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        403: {
            "description": "Operação proibida. Requer privilégios de administrador."
        }
    }
)
def listar_todos_usuarios(
    admin_atual: Annotated[Usuario, Depends(obter_admin_atual)],
    sessao: Session = Depends(get_session)
):
    """
    Retorna a lista de todos os usuários cadastrados na base de dados (Exclusivo para ADMIN).
    """
    usuarios = sessao.exec(select(Usuario).order_by(Usuario.id_usuario.asc())).all()
    return usuarios


# =====================================================================
# 4. CONSULTAR USUÁRIO POR ID (GET /api/v1/usuarios/{id_usuario}) — ADMIN
# =====================================================================
@router.get(
    "/{id_usuario}",
    response_model=UsuarioRespostaSchema,
    status_code=status.HTTP_200_OK,
    summary="Consultar usuário por ID (Administrador)",
    description=(
        "Busca e retorna os detalhes de um usuário específico pelo seu identificador. "
        "Esta operação é restrita exclusivamente a administradores."
    ),
    responses={
        200: {
            "description": "Usuário localizado e retornado com sucesso."
        },
        401: {
            "description": "Token de acesso ausente, inválido ou expirado."
        },
        403: {
            "description": "Operação proibida. Requer privilégios de administrador."
        },
        404: {
            "description": "Usuário não localizado com o ID informado."
        }
    }
)
def obter_usuario_por_id(
    id_usuario: int,
    admin_atual: Annotated[Usuario, Depends(obter_admin_atual)],
    sessao: Session = Depends(get_session)
):
    """
    Busca os detalhes cadastrais de um cliente específico (Exclusivo para ADMIN).
    """
    usuario = sessao.get(Usuario, id_usuario)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário não localizado com id={id_usuario}."
        )

    return usuario
   
   
# =====================================================================
# 5. CADASTRAR NOVO USUÁRIO (POST /api/v1/usuarios/) — PÚBLICO
# =====================================================================
@router.post(
    "/",
    response_model=UsuarioRespostaSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário",
    description=(
        "Cria uma nova conta de cliente no sistema com perfil FreeTrial "
        "e retorna os dados cadastrais salvos (sem expor a senha)."
    ),
    responses={
        201: {
            "description": "Usuário cadastrado com sucesso."
        },
        409: {
            "description": "Conflito de e-mail ou CPF já cadastrado no sistema."
        },
        422: {
            "description": "Dados enviados inválidos. Verifique os campos obrigatórios."
        }
    }
)
def cadastrar_usuario(
    dados: UsuarioCriarSchema,
    sessao: Session = Depends(get_session)
):
    """
    Cadastra um novo cliente na base de dados da aplicação.
    """
    email_limpo = dados.email.strip().lower()

    existente = sessao.exec(
        select(Usuario).where(Usuario.email == email_limpo)
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O e-mail informado já está cadastrado."
        )

    novo_usuario = Usuario(
        nome_usuario=dados.nome_usuario,
        email=email_limpo,
        senha_hash=obter_hash_senha(dados.senha),
        cpf=dados.cpf,
        telefone=dados.telefone,
        cep=dados.cep,
        logradouro=dados.logradouro,
        numero=dados.numero,
        bairro=dados.bairro,
        cidade=dados.cidade,
        uf=dados.uf,
        tipo_plano="FreeTrial",
        tipo_usuario="CLIENTE",
        flag_sincronizado=1,
        data_cadastro=datetime.now(timezone.utc).isoformat()
    )

    try:
        sessao.add(novo_usuario)
        sessao.commit()
        sessao.refresh(novo_usuario)
    except IntegrityError:
        sessao.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível cadastrar o usuário (e-mail ou CPF duplicado)."
        )

    return novo_usuario
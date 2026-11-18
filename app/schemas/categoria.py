"""
=============================================================================
AGILISTA API — SCHEMAS DE CATEGORIA (PYDANTIC DTOs)
=============================================================================

Este arquivo define as classes de validação e modelagem de dados (DTOs)
utilizadas pelo FastAPI e Pydantic v2 para receber, validar e responder
requisições HTTP referentes ao módulo de Categorias.

Define os contratos de entrada, atualização e resposta para o módulo de Categorias.
Aplica validações estritas de dados, impede payloads de edição vazios, sincroniza
inteligentemente os campos de status e rejeita valores nulos (null) explicitamente.

Responsabilidades Principais:
1. Garantir que o nome da categoria não venha vazio ou composto só por espaços.
2. Manter a sincronização automática entre 'ativo' (1/0) e 'status_categoria' ('ATIVO'/'INATIVO').
3. Rejeitar payloads de atualização vazios {} ou com valores nulos (null) explícitos.
4. Omitir o campo 'usuario_id' do payload de criação para que o backend atribua a posse.
5. Formatar o JSON final de resposta retornado para o aplicativo mobile.
"""

# Importa as estruturas de tipagem para restringir valores válidos (Literal) e campos opcionais (Optional)
from typing import Literal, Optional

# Importa as ferramentas essenciais do Pydantic v2 para criação de DTOs e validação estrita de dados
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =====================================================================
# 1. SCHEMA BASE (Campos Comuns e Regras Fundamentais)
# =====================================================================
class CategoriaBaseSchema(BaseModel):
    """
    Atributos base e validações essenciais compartilhadas entre os schemas do módulo.
    """
    # Campo obrigatório para o nome da categoria com restrições de tamanho na definição
    nome_categoria: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nome da categoria (ex: Hortifrúti, Padaria, Carnes)",
        examples=["Hortifrúti"]
    )
    
    # Campo numérico para controle de ativação no aplicativo (1 = Ativo, 0 = Inativo)
    ativo: int = Field(
        default=1,
        ge=0,
        le=1,
        description="Status de ativação da categoria (1 = Ativo, 0 = Inativo)",
        examples=[1]
    )
    
    # Campo de texto legível restrito estritamente aos valores "ATIVO" ou "INATIVO"
    status_categoria: Literal["ATIVO", "INATIVO"] = Field(
        default="ATIVO",
        description="Situação cadastral legível da categoria (ATIVO ou INATIVO)",
        examples=["ATIVO"]
    )

    # Validador de campo aplicado especificamente sobre 'nome_categoria'
    @field_validator("nome_categoria")
    @classmethod
    def validar_nome_nao_vazio(cls, v: str) -> str:
        """
        Garante que o nome da categoria não seja nulo, vazio ou composto apenas por espaços.
        Valida o limite mínimo de 2 e máximo de 100 caracteres APÓS a limpeza de espaços (strip).
        """
        # Rejeita o valor se for explicitamente None
        if v is None:
            raise ValueError("O nome da categoria não pode ser nulo.")
        
        # Remove espaços nas extremidades do texto para higienização
        texto_limpo = v.strip()
        
        # Verifica se o texto restante tem pelo menos 2 caracteres válidos
        if len(texto_limpo) < 2:
            raise ValueError("O nome da categoria deve conter no mínimo 2 caracteres válidos.")
            
        # Verifica se o texto excede o limite máximo permitido de 100 caracteres
        if len(texto_limpo) > 100:
            raise ValueError("O nome da categoria deve conter no máximo 100 caracteres.")
            
        # Retorna o texto devidamente limpo e validado
        return texto_limpo


# =====================================================================
# 2. SCHEMA DE CRIAÇÃO (Payload do POST)
# =====================================================================
class CategoriaCriarSchema(CategoriaBaseSchema):
    """
    Dados recebidos na requisição para cadastrar uma nova categoria personalizada.
    O usuario_id NÃO é enviado no corpo pelo app; ele é definido pelo backend.
    """

    # Validador executado após a estruturação dos dados no modelo Pydantic
    @model_validator(mode="after")
    def sincronizar_status_no_cadastro(self):
        """
        Mantém 'ativo' e 'status_categoria' sincronizados no cadastro.
        O campo enviado pelo aplicativo prevalece quando apenas um dos dois for informado.
        Rejeita a requisição caso valores contraditórios sejam enviados simultaneamente.
        """
        # Identifica os campos que foram explicitamente fornecidos no JSON de requisição
        campos_enviados = self.model_fields_set

        # Se enviou apenas 'ativo', ajusta o 'status_categoria' equivalente
        if "ativo" in campos_enviados and "status_categoria" not in campos_enviados:
            self.status_categoria = "ATIVO" if self.ativo == 1 else "INATIVO"
            
        # Se enviou apenas 'status_categoria', ajusta o 'ativo' equivalente
        elif "status_categoria" in campos_enviados and "ativo" not in campos_enviados:
            self.ativo = 1 if self.status_categoria == "ATIVO" else 0
            
        # Se enviou ambos os campos, verifica se há incoerência entre os valores
        elif self.ativo != (1 if self.status_categoria == "ATIVO" else 0):
            raise ValueError(
                "Os campos ativo e status_categoria possuem valores incompatíveis."
            )
            
        # Retorna a instância com os campos devidamente sincronizados
        return self


# =====================================================================
# 3. SCHEMA DE ATUALIZAÇÃO (Payload do PUT)
# =====================================================================
class CategoriaAtualizarSchema(BaseModel):
    """
    Campos permitidos para modificação parcial ou total de uma categoria personalizada.
    Garante que a requisição contenha pelo menos uma alteração válida e rejeita nulos explícitos.
    """
    # Campo opcional para atualização do nome
    nome_categoria: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Novo nome para a categoria"
    )
    
    # Campo opcional para atualização do status numérico
    ativo: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Alterar status de ativação (1 = Ativo, 0 = Inativo)"
    )
    
    # Campo opcional para atualização do status textual
    status_categoria: Optional[Literal["ATIVO", "INATIVO"]] = Field(
        default=None,
        description="Novo status cadastral (ATIVO ou INATIVO)"
    )

    # Validador executado ANTES da conversão de tipos pelo Pydantic (mode="before")
    @model_validator(mode="before")
    @classmethod
    def rejeitar_nulo_explicito(cls, dados):
        """
        Rejeita valores null enviados explicitamente no JSON pelo aplicativo.
        Campos omitidos no JSON continuam permitidos para atualizações parciais.
        """
        # Verifica se o payload bruto de entrada é um dicionário JSON
        if isinstance(dados, dict):
            # Itera sobre os campos permitidos para alteração
            for campo in ("nome_categoria", "ativo", "status_categoria"):
                # Se o campo está presente nas chaves do JSON e o seu valor é None, bloqueia
                if campo in dados and dados[campo] is None:
                    raise ValueError(
                        f"O campo '{campo}' não aceita valor nulo (null)."
                    )
        return dados

    # Validador para sanitização e checagem do nome quando enviado no payload de atualização
    @field_validator("nome_categoria")
    @classmethod
    def validar_nome_opcional(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida e higieniza o nome opcional, garantindo os limites de tamanho após o strip.
        """
        # Se o campo foi informado para edição, executa a validação
        if v is not None:
            texto_limpo = v.strip()
            
            # Verifica se o texto restante tem pelo menos 2 caracteres válidos
            if len(texto_limpo) < 2:
                raise ValueError("O nome da categoria deve conter no mínimo 2 caracteres válidos.")
                
            # Verifica se o texto excede o limite máximo permitido de 100 caracteres
            if len(texto_limpo) > 100:
                raise ValueError("O nome da categoria deve conter no máximo 100 caracteres.")
                
            return texto_limpo
            
        return v

    # Validador executado APÓS a leitura inicial dos campos no modelo de atualização
    @model_validator(mode="after")
    def validar_e_sincronizar_atualizacao(self):
        """
        1. Impede atualizações com payload totalmente vazio {}.
        2. Sincroniza os campos de status caso apenas um seja informado.
        3. Rejeita valores contraditórios se ambos forem enviados.
        """
        # Obtém a lista dos campos que o cliente efetivamente enviou no JSON
        campos_enviados = self.model_fields_set

        # Rejeita requisições enviadas sem nenhum campo para modificar
        if not campos_enviados:
            raise ValueError(
                "Informe pelo menos um campo para realizar a atualização."
            )

        # Se apenas 'ativo' foi informado na atualização, sincroniza 'status_categoria'
        if "ativo" in campos_enviados and "status_categoria" not in campos_enviados:
            self.status_categoria = "ATIVO" if self.ativo == 1 else "INATIVO"
            
        # Se apenas 'status_categoria' foi informado na atualização, sincroniza 'ativo'
        elif "status_categoria" in campos_enviados and "ativo" not in campos_enviados:
            self.ativo = 1 if self.status_categoria == "ATIVO" else 0
            
        # Se ambos os campos foram informados, rejeita se forem incompatíveis entre si
        elif (
            "ativo" in campos_enviados
            and "status_categoria" in campos_enviados
            and self.ativo != (1 if self.status_categoria == "ATIVO" else 0)
        ):
            raise ValueError(
                "Os campos ativo e status_categoria possuem valores incompatíveis."
            )
            
        return self


# =====================================================================
# 4. SCHEMA DE RESPOSTA (Payload de Saída em GET/POST/PUT)
# =====================================================================
class CategoriaRespostaSchema(CategoriaBaseSchema):
    """
    Estrutura completa devolvida pela API nas consultas e respostas de escrita.
    Representa o estado persistido da categoria no servidor.
    """
    # Identificador único (chave primária) gerado pelo banco de dados do servidor
    id_categoria: int = Field(
        description="Identificador único (PK) no banco do servidor"
    )
    
    # Campo opcional para controle do servidor de sincronização
    servidor_id: Optional[int] = Field(
        default=None, 
        description="Identificador no servidor de sync"
    )
    
    # Identificador do proprietário (NULL = Categoria Padrão Global; Valor = Categoria do Usuário)
    usuario_id: Optional[int] = Field(
        default=None, 
        description="NULL = Categoria Padrão Global; Valor = Categoria do Usuário"
    )
    
    # Indicador de sincronização do registro (1 = Sincronizado com sucesso)
    flag_sincronizado: int = Field(
        default=1, 
        description="Indicador de sincronização (1 = OK)"
    )

    # Configuração nativa do Pydantic v2 que permite converter modelos do SQLModel/ORM diretamente em DTOs
    model_config = ConfigDict(from_attributes=True)
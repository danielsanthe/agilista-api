/**
 * ============================================================================
 * AGILISTA WEB — CLIENTE HTTP E COMUNICAÇÃO COM A API (FETCH WRAPPER)
 * ============================================================================
 *
 * Responsabilidades:
 * - Centralizar todas as requisições HTTP para o backend FastAPI (/api/v1).
 * - Injetar automaticamente o token JWT (Bearer) armazenado no estado.
 * - Padronizar o tratamento e a formatação de erros de validação (422) e HTTP.
 * - Expor endpoints tanto para o perfil ADMIN quanto para o perfil CLIENTE.
 */

import { getState } from "./state.js";

// Prefixo base das rotas versionadas da API
const BASE_URL = "/api/v1";

/**
 * Extrai e formata mensagens de erro retornadas pelo FastAPI / Pydantic v2.
 */
function extrairMensagemErro(data, status) {
  if (!data || !data.detail) return `Erro HTTP ${status}`;
  if (typeof data.detail === "string") return data.detail;

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((err) => `${err.loc ? err.loc[err.loc.length - 1] : "Campo"}: ${err.msg}`)
      .join(" | ");
  }

  return JSON.stringify(data.detail);
}

/**
 * Executa uma requisição HTTP autenticada e trata a resposta JSON.
 */
async function request(endpoint, options = {}) {
  const { token } = getState();
  const isFormUrlEncoded =
    options.headers?.["Content-Type"] === "application/x-www-form-urlencoded";

  const headers = {
    ...(!isFormUrlEncoded ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extrairMensagemErro(data, response.status));
  }

  return data;
}

/**
 * Objeto exportado com todos os métodos de consumo dos recursos da API.
 */
export const api = {
  // ==========================================================================
  // 1. AUTENTICAÇÃO E PERFIL
  // ==========================================================================
  async login(email, senha) {
    return request("/auth/signin", {
      method: "POST",
      body: JSON.stringify({
        email: email,
        password: senha,
      }),
    });
  },

  obterPerfilMe: () => request("/usuarios/me"),

  // ==========================================================================
  // 2. PRODUTOS GLOBAIS (ADMIN — CONSULTA PAGINADA + CRUD)
  // ==========================================================================
  listarProdutosGlobaisPaginado: ({ busca = "", categoriaId = "", limit = 25, offset = 0 } = {}) => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));

    if (busca && busca.trim()) {
      params.set("busca", busca.trim());
    }
    if (categoriaId) {
      params.set("categoria_id", String(categoriaId));
    }

    return request(`/produtos-globais/paginado?${params.toString()}`);
  },

  criarProdutoGlobal: (payload) =>
    request("/produtos-globais/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  atualizarProdutoGlobal: (id, payload) =>
    request(`/produtos-globais/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  removerProdutoGlobal: (id) =>
    request(`/produtos-globais/${id}`, { method: "DELETE" }),

  // ==========================================================================
  // 3. CATEGORIAS (PADRÃO DO SISTEMA + PERSONALIZADAS DO USUÁRIO)
  // ==========================================================================
  listarCategorias: () => request("/categorias/"),

  // ==========================================================================
  // 4. USUÁRIOS E CLIENTES (EXCLUSIVO ADMIN)
  // ==========================================================================
  listarUsuarios: () => request("/usuarios/"),

  // ==========================================================================
  // 5. RECURSOS DO USUÁRIO CLIENTE (LISTAS, ITENS E CATÁLOGO PESSOAL)
  // ==========================================================================
  listarMinhasListas: () => request("/listas/?status=todas"),

  listarItensDaLista: (idLista) => request(`/listas/${idLista}/itens`),

  listarMeusProdutos: () => request("/produtos/"),
};
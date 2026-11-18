/**
 * ============================================================================
 * AGILISTA WEB — GERENCIADOR DE ESTADO CENTRALIZADO
 * ============================================================================
 *
 * Implementa o padrão Publish-Subscribe para manter a interface sincronizada
 * com os dados carregados da API tanto para o perfil ADMIN quanto CLIENTE.
 */

const listeners = new Set();

const state = {
  token: localStorage.getItem("agilista_web_token") || null,
  usuario: null,

  // Navegação principal (menu lateral) e sub-aba de Produtos Globais
  abaAtiva: "produtos-globais", // ADMIN: 'produtos-globais' | 'categorias' | 'usuarios'
                                // CLIENTE: 'minhas-listas' | 'meus-produtos' | 'minhas-categorias'
  subAbaProdutos: "consulta",   // 'consulta' | 'cadastro'
  menuAberto: window.innerWidth > 768,

  // Dados paginados e filtros de Produtos Globais (ADMIN)
  produtosGlobais: [],
  totalProdutosGlobais: 0,
  filtroBuscaProduto: "",
  filtroCategoriaProduto: "",
  paginaAtualProdutos: 1,
  itensPorPaginaProdutos: 25,
  buscandoProdutos: false,
  produtoEmEdicao: null,

  // Dados compartilhados e exclusivos do CLIENTE
  categorias: [],
  usuarios: [],
  minhasListas: [],
  meusProdutos: [],
  filtroStatusLista: "todas",
  filtroBuscaMeuProduto: "",

  // Modal de visualização de itens de uma lista (CLIENTE)
  listaSelecionadaModal: null,
  itensListaModal: [],
  carregandoItensModal: false,

  // Mensagens de feedback visual (erro e sucesso)
  erro: null,
  sucesso: null,
  carregando: false,
};

/**
 * Retorna uma cópia rasa (shallow copy) do estado atual.
 */
export function getState() {
  return { ...state };
}

/**
 * Atualiza parcialmente o estado e notifica todos os inscritos (ex: renderApp).
 */
export function setState(parcial) {
  Object.assign(state, parcial);
  listeners.forEach((fn) => fn(getState()));
}

/**
 * Inscreve uma função observadora nas mudanças de estado.
 */
export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
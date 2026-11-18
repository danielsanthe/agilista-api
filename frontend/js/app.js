/**
 * ============================================================================
 * AGILISTA WEB — CONTROLADOR PRINCIPAL E EVENTOS (ADMIN & CLIENTE)
 * ============================================================================
 *
 * Responsabilidades:
 * - Autenticar e carregar o painel correspondente ao perfil (`ADMIN` ou `CLIENTE`).
 * - Gerenciar filtros, paginação, sub-abas e CRUD administrativo.
 * - Permitir que o usuário CLIENTE visualize suas listas, itens, produtos e categorias,
 *   além de atualizar os dados sincronizados com o aplicativo mobile.
 */

import { getState, setState, subscribe } from "./state.js";
import { api } from "./api.js";
import { renderApp } from "./render.js";

subscribe(renderApp);

// Temporizador para ocultar mensagens de sucesso automaticamente
let timerMensagemSucesso = null;

/**
 * Exibe uma mensagem verde de confirmação por 4 segundos.
 */
function exibirSucesso(mensagem) {
  clearTimeout(timerMensagemSucesso);
  setState({ sucesso: mensagem, erro: null });
  timerMensagemSucesso = setTimeout(() => {
    setState({ sucesso: null });
  }, 4000);
}

/**
 * Consulta a página atual de produtos globais aplicando os filtros ativos no estado (ADMIN).
 */
async function buscarProdutosFiltrados(novaPagina = null) {
  const atual = getState();
  const pagina = novaPagina !== null ? novaPagina : atual.paginaAtualProdutos;
  const limit = atual.itensPorPaginaProdutos;
  const offset = (pagina - 1) * limit;

  try {
    setState({ buscandoProdutos: true, erro: null });
    const resposta = await api.listarProdutosGlobaisPaginado({
      busca: atual.filtroBuscaProduto,
      categoriaId: atual.filtroCategoriaProduto,
      limit,
      offset,
    });

    setState({
      produtosGlobais: resposta.itens,
      totalProdutosGlobais: resposta.total,
      paginaAtualProdutos: pagina,
      buscandoProdutos: false,
    });
  } catch (err) {
    setState({ buscandoProdutos: false, erro: err.message });
  }
}

/**
 * Carrega os dados iniciais do painel de acordo com o perfil do usuário (`ADMIN` ou `CLIENTE`).
 */
async function carregarDadosPainel(mostrarAlertaAtualizacao = false) {
  try {
    setState({ carregando: true, erro: null });
    const perfil = await api.obterPerfilMe();

    // Fluxo 1: Perfil Administrador
    if (perfil.tipo_usuario === "ADMIN") {
      const { itensPorPaginaProdutos } = getState();

      const [respostaProdutos, categorias, usuarios] = await Promise.all([
        api.listarProdutosGlobaisPaginado({ limit: itensPorPaginaProdutos, offset: 0 }),
        api.listarCategorias(),
        api.listarUsuarios(),
      ]);

      setState({
        usuario: perfil,
        abaAtiva: "produtos-globais",
        produtosGlobais: respostaProdutos.itens,
        totalProdutosGlobais: respostaProdutos.total,
        paginaAtualProdutos: 1,
        categorias,
        usuarios,
        carregando: false,
      });
      return;
    }

    // Fluxo 2: Perfil Usuário Cliente (sincronizado com o App Mobile)
    const [minhasListas, meusProdutos, categorias] = await Promise.all([
      api.listarMinhasListas(),
      api.listarMeusProdutos(),
      api.listarCategorias(),
    ]);

    const abaAtual = getState().abaAtiva;
    const abasValidasCliente = ["minhas-listas", "meus-produtos", "minhas-categorias"];
    const abaInicialCliente = abasValidasCliente.includes(abaAtual)
      ? abaAtual
      : "minhas-listas";

    setState({
      usuario: perfil,
      abaAtiva: abaInicialCliente,
      minhasListas,
      meusProdutos,
      categorias,
      carregando: false,
    });

    if (mostrarAlertaAtualizacao) {
      exibirSucesso("Dados atualizados com sucesso a partir do servidor!");
    }
  } catch (err) {
    localStorage.removeItem("agilista_web_token");
    setState({
      token: null,
      usuario: null,
      carregando: false,
      erro: err.message,
    });
  }
}

// ============================================================================
// DELEGAÇÃO GLOBAL DE EVENTOS DE FORMULÁRIO (SUBMIT)
// ============================================================================
document.addEventListener("submit", async (e) => {
  e.preventDefault();

  // 1. Login Unificado (ADMIN ou CLIENTE)
  if (e.target.id === "form-login") {
    const fd = new FormData(e.target);
    try {
      setState({ carregando: true, erro: null });
      const res = await api.login(fd.get("email"), fd.get("senha"));
      localStorage.setItem("agilista_web_token", res.access_token);
      setState({ token: res.access_token });
      await carregarDadosPainel();
    } catch (err) {
      setState({ carregando: false, erro: err.message });
    }
    return;
  }

  // 2. Consulta Sob Demanda de Produtos Globais (ADMIN)
  if (e.target.id === "form-consulta-produtos") {
    const fd = new FormData(e.target);
    setState({
      filtroBuscaProduto: String(fd.get("busca") || "").trim(),
      filtroCategoriaProduto: String(fd.get("categoria_id") || ""),
      paginaAtualProdutos: 1,
      sucesso: null,
    });
    await buscarProdutosFiltrados(1);
    return;
  }

  // 3. Cadastro ou Edição de Produto Global (ADMIN)
  if (e.target.id === "form-produto-global") {
    const fd = new FormData(e.target);
    const { produtoEmEdicao } = getState();

    const payload = {
      codigo_barras: String(fd.get("codigo_barras")).trim(),
      nome_oficial: String(fd.get("nome_oficial")).trim(),
      unidade_medida_padrao: String(fd.get("unidade_medida_padrao")).trim(),
      categoria_id: Number(fd.get("categoria_id")),
    };

    try {
      setState({ erro: null, sucesso: null });

      if (produtoEmEdicao) {
        await api.atualizarProdutoGlobal(produtoEmEdicao.id_produto_global, payload);
        setState({ produtoEmEdicao: null, subAbaProdutos: "consulta" });
        await buscarProdutosFiltrados();
        exibirSucesso("Produto atualizado com sucesso!");
      } else {
        await api.criarProdutoGlobal(payload);
        e.target.reset();
        await buscarProdutosFiltrados(1);
        exibirSucesso("Produto cadastrado com sucesso!");
      }
    } catch (err) {
      setState({ erro: err.message });
    }
  }
});

// ============================================================================
// DELEGAÇÃO GLOBAL DE EVENTOS DE CLIQUE (CLICK)
// ============================================================================
document.addEventListener("click", async (e) => {
  // 1. Logout
  if (e.target.closest("#btn-logout")) {
    localStorage.removeItem("agilista_web_token");
    setState({
      token: null,
      usuario: null,
      produtoEmEdicao: null,
      listaSelecionadaModal: null,
      itensListaModal: [],
      erro: null,
      sucesso: null,
    });
    return;
  }

  // 2. Atualizar Dados Sincronizados (Botão "Sincronizar / Atualizar" no topo)
  if (e.target.closest("#btn-refresh-cliente")) {
    await carregarDadosPainel(true);
    return;
  }

  // 3. Toggle Menu Lateral (Ícone Sanduíche)
  if (e.target.closest("#btn-toggle-menu")) {
    const { menuAberto } = getState();
    setState({ menuAberto: !menuAberto });
    return;
  }

  // 4. Troca de Seção no Menu Lateral
  const btnTab = e.target.closest("[data-tab]");
  if (btnTab) {
    const tab = btnTab.dataset.tab;
    const fecharNoMobile = window.innerWidth <= 768 ? false : getState().menuAberto;
    setState({
      abaAtiva: tab,
      menuAberto: fecharNoMobile,
      produtoEmEdicao: null,
      erro: null,
      sucesso: null,
    });
    return;
  }

  // 5. Troca de Sub-aba Interna (Consulta vs Cadastro — ADMIN)
  const btnSubTab = e.target.closest("[data-subtab]");
  if (btnSubTab) {
    const subAba = btnSubTab.dataset.subtab;
    setState({
      subAbaProdutos: subAba,
      produtoEmEdicao: subAba === "cadastro" ? null : getState().produtoEmEdicao,
      erro: null,
      sucesso: null,
    });
    return;
  }

  // 6. Filtro de Status das Listas (CLIENTE)
  const btnFiltroStatus = e.target.closest("[data-status-lista]");
  if (btnFiltroStatus) {
    setState({ filtroStatusLista: btnFiltroStatus.dataset.statusLista });
    return;
  }

  // 7. Abrir Modal de Itens de uma Lista (CLIENTE)
  const btnVerItens = e.target.closest("[data-ver-itens-lista]");
  if (btnVerItens) {
    const idLista = Number(btnVerItens.dataset.verItensLista);
    const lista = getState().minhasListas.find((l) => (l.id_lista ?? l.id) === idLista);
    if (!lista) return;

    setState({
      listaSelecionadaModal: lista,
      itensListaModal: [],
      carregandoItensModal: true,
      erro: null,
    });

    try {
      const itens = await api.listarItensDaLista(idLista);
      setState({
        itensListaModal: itens,
        carregandoItensModal: false,
      });
    } catch (err) {
      setState({
        carregandoItensModal: false,
        erro: err.message,
      });
    }
    return;
  }

  // 8. Fechar Modal de Itens da Lista (CLIENTE)
  if (
    e.target.closest("#btn-fechar-modal-itens") ||
    e.target.id === "modal-itens-overlay"
  ) {
    setState({
      listaSelecionadaModal: null,
      itensListaModal: [],
      carregandoItensModal: false,
    });
    return;
  }

  // 9. Limpar Filtros de Pesquisa (ADMIN)
  if (e.target.closest("#btn-limpar-filtros")) {
    setState({
      filtroBuscaProduto: "",
      filtroCategoriaProduto: "",
      paginaAtualProdutos: 1,
      sucesso: null,
    });
    await buscarProdutosFiltrados(1);
    return;
  }

  // 10. Paginação (Página Anterior / Próxima — ADMIN)
  const btnPagina = e.target.closest("[data-page]");
  if (btnPagina && !btnPagina.disabled) {
    const destino = Number(btnPagina.dataset.page);
    await buscarProdutosFiltrados(destino);
    return;
  }

  // 11. Iniciar Edição de Produto Global (ADMIN)
  const btnEditar = e.target.closest("[data-edit-produto]");
  if (btnEditar) {
    const idEditar = Number(btnEditar.dataset.editProduto);
    const produto = getState().produtosGlobais.find(
      (p) => p.id_produto_global === idEditar
    );
    if (produto) {
      setState({
        produtoEmEdicao: produto,
        subAbaProdutos: "cadastro",
        erro: null,
        sucesso: null,
      });
    }
    return;
  }

  // 12. Cancelar Edição (ADMIN)
  if (e.target.closest("#btn-cancelar-edicao")) {
    setState({
      produtoEmEdicao: null,
      subAbaProdutos: "consulta",
      erro: null,
      sucesso: null,
    });
    return;
  }

  // 13. Excluir Produto Global (ADMIN)
  const btnExcluir = e.target.closest("[data-delete-produto]");
  if (btnExcluir) {
    const idExcluir = Number(btnExcluir.dataset.deleteProduto);
    if (confirm("Deseja realmente excluir este produto global?")) {
      try {
        await api.removerProdutoGlobal(idExcluir);
        const { produtoEmEdicao } = getState();
        const manterEdicao =
          produtoEmEdicao && produtoEmEdicao.id_produto_global === idExcluir
            ? null
            : produtoEmEdicao;

        setState({ produtoEmEdicao: manterEdicao });
        await buscarProdutosFiltrados();
        exibirSucesso("Produto excluído com sucesso!");
      } catch (err) {
        setState({ erro: err.message });
      }
    }
  }
});

// Filtro instantâneo na busca de produtos do cliente
document.addEventListener("input", (e) => {
  if (e.target.id === "input-busca-meu-produto") {
    setState({ filtroBuscaMeuProduto: e.target.value });
  }
});

// ============================================================================
// INICIALIZAÇÃO DA APLICAÇÃO
// ============================================================================
if (getState().token) {
  carregarDadosPainel();
} else {
  renderApp(getState());
}
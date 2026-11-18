/**
 * ============================================================================
 * AGILISTA WEB — CAMADA DE RENDERIZAÇÃO DA INTERFACE (HTML TEMPLATE)
 * ============================================================================
 *
 * Responsabilidades:
 * - Renderizar a tela de login unificada para Administradores e Clientes.
 * - Renderizar o cabeçalho com botão sanduíche, menu lateral retrátil e
 *   conteúdo específico conforme o perfil autenticado (`ADMIN` ou `CLIENTE`).
 * - Renderizar para o perfil CLIENTE:
 *   1. Minhas Listas de Compras + Modal detalhado dos Itens da Lista.
 *   2. Meus Produtos Cadastrados (Catálogo Privado).
 *   3. Minhas Categorias (Padrão do Sistema + Personalizadas).
 */

/**
 * Escapa aspas duplas em atributos HTML para evitar quebra de layout.
 */
function escaparAtributo(valor) {
  if (valor === null || valor === undefined) return "";
  return String(valor).replace(/"/g, "&quot;");
}

/**
 * Formata números inteiros no padrão brasileiro.
 */
function formatarNumero(valor) {
  return Number(valor || 0).toLocaleString("pt-BR");
}

/**
 * Formata valores monetários em Real Brasileiro (R$).
 */
function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

/**
 * Formata datas ISO-8601 para o padrão dd/mm/aaaa HH:mm.
 */
function formatarDataHora(isoString) {
  if (!isoString) return "-";
  const data = new Date(isoString);
  if (Number.isNaN(data.getTime())) return isoString;
  return data.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Retorna a classe CSS de destaque conforme o status da lista.
 */
function classeBadgeStatusLista(status) {
  if (status === "Concluída") return "badge-success";
  if (status === "Em Andamento") return "badge-warning";
  return "";
}

/**
 * Renderiza toda a estrutura da aplicação dentro de #app.
 */
export function renderApp(state) {
  const root = document.getElementById("app");

  // Tela de Login Unificada (ADMIN ou CLIENTE) — sem e-mail de exemplo exposto
  if (!state.token || !state.usuario) {
    root.innerHTML = `
      <div class="login-container">
        <div class="card">
          <div class="login-header">
            <img src="./img/logo.png" alt="Logo AgiLista" class="login-logo" />
            <h1>AgiLista Web</h1>
            <p>Acesse com sua conta de Cliente ou Administrador.</p>
          </div>
          ${state.erro ? `<div class="alert">${state.erro}</div>` : ""}
          <form id="form-login" autocomplete="off">
            <div class="form-group">
              <label for="input-login-email">E-mail</label>
              <input
                type="email"
                id="input-login-email"
                name="email"
                required
                autocomplete="username"
                placeholder="Informe seu e-mail"
              />
            </div>
            <div class="form-group">
              <label for="input-login-senha">Senha</label>
              <input
                type="password"
                id="input-login-senha"
                name="senha"
                required
                autocomplete="current-password"
                placeholder="Informe sua senha"
              />
            </div>
            <button type="submit" style="width: 100%;" ${state.carregando ? "disabled" : ""}>
              ${state.carregando ? "Autenticando..." : "Entrar"}
            </button>
          </form>
        </div>
      </div>
    `;
    return;
  }

  const isAdmin = state.usuario.tipo_usuario === "ADMIN";

  // Monta os itens do menu lateral conforme o perfil do usuário
  const menuLateralHtml = isAdmin
    ? `
      <div class="sidebar-section-title">Administração</div>

      <button
        type="button"
        data-tab="produtos-globais"
        class="sidebar-item ${state.abaAtiva === "produtos-globais" ? "active" : ""}"
      >
        <span>Cadastro Produtos Globais</span>
        <span class="sidebar-count">${formatarNumero(state.totalProdutosGlobais)}</span>
      </button>

      <button
        type="button"
        data-tab="categorias"
        class="sidebar-item ${state.abaAtiva === "categorias" ? "active" : ""}"
      >
        <span>Categorias Padrão</span>
        <span class="sidebar-count">${formatarNumero(state.categorias.length)}</span>
      </button>

      <button
        type="button"
        data-tab="usuarios"
        class="sidebar-item ${state.abaAtiva === "usuarios" ? "active" : ""}"
      >
        <span>Clientes / Usuários</span>
        <span class="sidebar-count">${formatarNumero(state.usuarios.length)}</span>
      </button>

      <div class="sidebar-footer">
        <div class="sidebar-section-title">Desenvolvedor</div>
        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          class="sidebar-item sidebar-link-docs"
          title="Abrir documentação interativa Swagger UI em nova aba"
        >
          <span>API - Swagger UI (/docs)</span>
          <span class="sidebar-external-icon">↗</span>
        </a>
      </div>
    `
    : `
      <div class="sidebar-section-title">Minha Conta</div>

      <button
        type="button"
        data-tab="minhas-listas"
        class="sidebar-item ${state.abaAtiva === "minhas-listas" ? "active" : ""}"
      >
        <span>Minhas Listas</span>
        <span class="sidebar-count">${formatarNumero(state.minhasListas.length)}</span>
      </button>

      <button
        type="button"
        data-tab="meus-produtos"
        class="sidebar-item ${state.abaAtiva === "meus-produtos" ? "active" : ""}"
      >
        <span>Meus Produtos</span>
        <span class="sidebar-count">${formatarNumero(state.meusProdutos.length)}</span>
      </button>

      <button
        type="button"
        data-tab="minhas-categorias"
        class="sidebar-item ${state.abaAtiva === "minhas-categorias" ? "active" : ""}"
      >
        <span>Categorias</span>
        <span class="sidebar-count">${formatarNumero(state.categorias.length)}</span>
      </button>

      <div class="sidebar-footer">
        <div class="sidebar-section-title">Sincronização App</div>
        <button
          type="button"
          id="btn-refresh-cliente"
          class="sidebar-item"
          title="Recarregar listas e produtos sincronizados pelo aplicativo"
        >
          <span>↻ Atualizar Dados</span>
        </button>
      </div>
    `;

  root.innerHTML = `
    <header>
      <div class="brand-area">
        <button
          type="button"
          id="btn-toggle-menu"
          class="btn-hamburger"
          title="${state.menuAberto ? "Recolher menu" : "Expandir menu"}"
          aria-label="Alternar menu lateral"
        >
          ☰
        </button>
        <img src="./img/logo.png" alt="Logo AgiLista" class="header-logo" />
        <div>
          <span class="brand-title">AgiLista</span>
          <span class="brand-subtitle">• ${isAdmin ? "Painel Administrativo" : "Área do Cliente"}</span>
        </div>
      </div>
      <div class="user-area">
        <span>Olá, <strong>${state.usuario.nome_usuario}</strong></span>
        <button id="btn-logout" class="btn-outline">Sair</button>
      </div>
    </header>

    <div class="layout-wrapper">
      <!-- MENU LATERAL RETRÁTIL -->
      <aside id="sidebar-menu" class="sidebar ${state.menuAberto ? "" : "collapsed"}">
        ${menuLateralHtml}
      </aside>

      <!-- ÁREA PRINCIPAL DE CONTEÚDO -->
      <main>
        ${state.erro ? `<div class="alert">${state.erro}</div>` : ""}
        ${state.sucesso ? `<div class="alert-success">✓ ${state.sucesso}</div>` : ""}
        ${isAdmin ? renderAbaAdmin(state) : renderAbaCliente(state)}
      </main>
    </div>

    ${renderModalItensLista(state)}
  `;
}

// ============================================================================
// RENDERIZAÇÃO DO PAINEL DO CLIENTE
// ============================================================================
function renderAbaCliente(state) {
  const mapaCategorias = Object.fromEntries(
    state.categorias.map((c) => [c.id_categoria ?? c.id, c.nome_categoria])
  );

  // 1. ABA: MINHAS LISTAS DE COMPRAS
  if (state.abaAtiva === "minhas-listas") {
    const listasFiltradas = state.minhasListas.filter((l) => {
      if (state.filtroStatusLista === "todas") return true;
      return l.status_lista === state.filtroStatusLista;
    });

    const linhas = listasFiltradas
      .map((l) => {
        const idLista = l.id_lista ?? l.id;
        return `
        <tr>
          <td>#${idLista}</td>
          <td><strong>${l.nome_lista}</strong></td>
          <td>${l.nome_estabelecimento || "-"}</td>
          <td><span class="badge ${classeBadgeStatusLista(l.status_lista)}">${l.status_lista}</span></td>
          <td>${formatarMoeda(l.valor_orcamento)}</td>
          <td><strong>${formatarMoeda(l.valor_total_atual)}</strong></td>
          <td>${formatarDataHora(l.data_criacao)}</td>
          <td>
            <button
              type="button"
              class="btn-edit"
              data-ver-itens-lista="${idLista}"
            >
              Ver Itens
            </button>
          </td>
        </tr>`;
      })
      .join("");

    return `
      <div class="panel">
        <div class="panel-header-row">
          <h2>Minhas Listas de Compras (${formatarNumero(listasFiltradas.length)})</h2>
          <button type="button" id="btn-refresh-cliente" class="btn-orange" style="height: 38px;">
            ↻ Sincronizar Agora
          </button>
        </div>

        <!-- FILTRO POR STATUS DA LISTA -->
        <div class="mobile-segmented-tabs">
          <button
            type="button"
            data-status-lista="todas"
            class="segmented-tab ${state.filtroStatusLista === "todas" ? "active" : ""}"
          >
            Todas (${formatarNumero(state.minhasListas.length)})
          </button>
          <button
            type="button"
            data-status-lista="Planejada"
            class="segmented-tab ${state.filtroStatusLista === "Planejada" ? "active" : ""}"
          >
            Planejadas
          </button>
          <button
            type="button"
            data-status-lista="Em Andamento"
            class="segmented-tab ${state.filtroStatusLista === "Em Andamento" ? "active" : ""}"
          >
            Em Andamento
          </button>
          <button
            type="button"
            data-status-lista="Concluída"
            class="segmented-tab ${state.filtroStatusLista === "Concluída" ? "active" : ""}"
          >
            Concluídas
          </button>
        </div>

        <div class="table-scroll-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nome da Lista</th>
                <th>Estabelecimento</th>
                <th>Status</th>
                <th>Orçamento</th>
                <th>Total Atual</th>
                <th>Criada em</th>
                <th>Detalhes</th>
              </tr>
            </thead>
            <tbody>
              ${
                linhas ||
                `<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">Nenhuma lista encontrada. Crie uma lista no aplicativo ÁgiLista e sincronize!</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 2. ABA: MEUS PRODUTOS CADASTRADOS
  if (state.abaAtiva === "meus-produtos") {
    const termo = (state.filtroBuscaMeuProduto || "").trim().toLowerCase();
    const produtosFiltrados = state.meusProdutos.filter((p) => {
      if (!termo) return true;
      return (
        (p.nome_produto || "").toLowerCase().includes(termo) ||
        (p.codigo_barras || "").toLowerCase().includes(termo)
      );
    });

    const linhas = produtosFiltrados
      .map((p, idx) => {
        const idProduto = p.id_produto ?? p.id ?? p.id_produto_usuario ?? (idx + 1);
        return `
        <tr>
          <td>#${idProduto}</td>
          <td><strong>${p.nome_produto}</strong></td>
          <td>${p.codigo_barras || "-"}</td>
          <td>${p.unidade_medida}</td>
          <td>${mapaCategorias[p.categoria_id] || `Categoria #${p.categoria_id}`}</td>
          <td>
            <span class="badge ${p.flag_produto_recorrente === 1 ? "badge-admin" : ""}">
              ${p.flag_produto_recorrente === 1 ? "Recorrente" : "Normal"}
            </span>
          </td>
        </tr>`;
      })
      .join("");

    return `
      <div class="panel">
        <div class="panel-header-row">
          <h2>Meus Produtos (${formatarNumero(produtosFiltrados.length)})</h2>
          <button type="button" id="btn-refresh-cliente" class="btn-orange" style="height: 38px;">
            ↻ Sincronizar Agora
          </button>
        </div>

        <div class="filter-bar">
          <div class="filter-search">
            <label for="input-busca-meu-produto">Pesquisar Produto ou Código de Barras</label>
            <input
              type="search"
              id="input-busca-meu-produto"
              value="${escaparAtributo(state.filtroBuscaMeuProduto)}"
              placeholder="Digite o nome do produto ou EAN..."
            />
          </div>
        </div>

        <div class="table-scroll-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Produto</th>
                <th>Código de Barras</th>
                <th>Unidade</th>
                <th>Categoria</th>
                <th>Tipo</th>
              </tr>
            </thead>
            <tbody>
              ${
                linhas ||
                `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Nenhum produto encontrado no seu catálogo pessoal.</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // 3. ABA: CATEGORIAS (PADRÃO + PERSONALIZADAS DO CLIENTE)
  const linhasCategorias = state.categorias
    .map((c) => {
      const idCategoria = c.id_categoria ?? c.id;
      return `
      <tr>
        <td>#${idCategoria}</td>
        <td><strong>${c.nome_categoria}</strong></td>
        <td>
          <span class="badge ${c.usuario_id !== null ? "badge-admin" : ""}">
            ${c.usuario_id === null ? "Sistema (Padrão)" : "Personalizada (Minha)"}
          </span>
        </td>
        <td><span class="badge badge-success">${c.status_categoria}</span></td>
      </tr>`;
    })
    .join("");

  return `
    <div class="panel">
      <div class="panel-header-row">
        <h2>Categorias Disponíveis (${formatarNumero(state.categorias.length)})</h2>
        <button type="button" id="btn-refresh-cliente" class="btn-orange" style="height: 38px;">
          ↻ Sincronizar Agora
        </button>
      </div>

      <div class="table-scroll-container">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nome da Categoria</th>
              <th>Origem</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${
              linhasCategorias ||
              `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Nenhuma categoria disponível.</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;
}

/**
 * Renderiza o Modal com os Itens da Lista selecionada pelo Cliente.
 * - Lista Concluída: exibe o `nome_produto` oficial do cadastro do usuário
 *   (usando `nome_item_planejado` apenas se não houver produto vinculado).
 * - Lista Planejada (ou Em Andamento): exibe sempre `item.nome_item_planejado`.
 */
function renderModalItensLista(state) {
  const lista = state.listaSelecionadaModal;
  if (!lista) return "";

  // Mapa rápido id_produto -> nome_produto a partir do catálogo pessoal já carregado
  const mapaProdutosPorId = Object.fromEntries(
    (state.meusProdutos || []).map((p) => [
      Number(p.id_produto ?? p.id ?? p.id_produto_usuario),
      p.nome_produto,
    ])
  );

  const isListaConcluida = lista.status_lista === "Concluída";

  // Cálculo do saldo restante igual ao aplicativo mobile (Orçamento - Total Atual)
  const orcamento = Number(lista.valor_orcamento || 0);
  const totalAtual = Number(lista.valor_total_atual || 0);
  const restante = orcamento - totalAtual;
  const corRestante =
    restante < 0 ? "var(--status-danger)" : "var(--status-success)";

  const linhasItens = state.itensListaModal
    .map((item) => {
      const produtoId = Number(item.produto_id ?? item.produto?.id_produto ?? 0);
      const nomeCadastro =
        item.produto?.nome_produto ||
        (produtoId > 0 ? mapaProdutosPorId[produtoId] : null);

      const nomeExibicao =
        isListaConcluida && nomeCadastro
          ? nomeCadastro
          : item.nome_item_planejado;

      return `
      <tr>
        <td>
          <strong>${nomeExibicao}</strong>
          ${
            item.flag_fora_da_lista === 1
              ? `<span class="badge badge-admin" style="margin-left:6px;">Fora da Lista</span>`
              : ""
          }
          ${
            item.flag_promocao === 1
              ? `<span class="badge badge-success" style="margin-left:6px;">Promoção</span>`
              : ""
          }
        </td>
        <td>${item.qtd_planejada}</td>
        <td>${item.qtd_comprada || 0}</td>
        <td>${formatarMoeda(item.preco_unitario || item.preco_estimado)}</td>
        <td><strong>${formatarMoeda(item.subtotal_item)}</strong></td>
        <td><span class="badge">${item.status_item}</span></td>
      </tr>`;
    })
    .join("");

  return `
    <div id="modal-itens-overlay" class="modal-overlay">
      <div class="modal-box">
        <div class="panel-header-row">
          <div>
            <h2 style="margin-bottom: 4px;">${lista.nome_lista}</h2>
            <span style="color: var(--text-muted); font-size: 13px;">
              Estabelecimento: <strong>${lista.nome_estabelecimento || "-"}</strong> •
              Orçamento: <strong>${formatarMoeda(orcamento)}</strong> •
              Total Atual: <strong>${formatarMoeda(totalAtual)}</strong> •
              Restante: <strong style="color: ${corRestante};">${formatarMoeda(restante)}</strong>
            </span>
          </div>
          <button type="button" id="btn-fechar-modal-itens" class="btn-secondary">
            ✕ Fechar
          </button>
        </div>

        <div class="table-scroll-container" style="max-height: 55vh;">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Qtd. Planejada</th>
                <th>Qtd. Comprada</th>
                <th>Preço Unit.</th>
                <th>Subtotal</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${
                state.carregandoItensModal
                  ? `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Carregando itens da lista...</td></tr>`
                  : linhasItens ||
                    `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Nenhum item registrado nesta lista.</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

// ============================================================================
// RENDERIZAÇÃO DO PAINEL ADMINISTRATIVO (ORIGINAL MANTIDO)
// ============================================================================
function renderAbaAdmin(state) {
  if (state.abaAtiva === "produtos-globais") {
    const editando = state.produtoEmEdicao;
    const subAba = state.subAbaProdutos;

    return `
      <div class="panel">
        <div class="panel-header-row">
          <h2>Catálogo Global de Produtos</h2>
          ${
            editando
              ? `<span class="editing-pill">Editando Produto #${editando.id_produto_global}</span>`
              : ""
          }
        </div>

        <div class="mobile-segmented-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected="${subAba === "consulta"}"
            data-subtab="consulta"
            class="segmented-tab ${subAba === "consulta" ? "active" : ""}"
          >
            🔍 Consulta (${formatarNumero(state.totalProdutosGlobais)})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected="${subAba === "cadastro"}"
            data-subtab="cadastro"
            class="segmented-tab ${subAba === "cadastro" ? "active" : ""}"
          >
            ${editando ? `✏️ Editar #${editando.id_produto_global}` : "➕ Cadastro"}
          </button>
        </div>

        ${
          subAba === "cadastro"
            ? renderSubAbaCadastroProduto(state)
            : renderSubAbaConsultaProduto(state)
        }
      </div>
    `;
  }

  if (state.abaAtiva === "categorias") {
    const linhas = state.categorias
      .map(
        (c) => `
        <tr>
          <td>#${c.id_categoria}</td>
          <td><strong>${c.nome_categoria}</strong></td>
          <td>${c.usuario_id === null ? "Sistema (Padrão)" : `Usuário #${c.usuario_id}`}</td>
          <td><span class="badge">${c.status_categoria}</span></td>
        </tr>`
      )
      .join("");

    return `
      <div class="panel">
        <h2>Categorias do Sistema</h2>
        <div class="table-scroll-container">
          <table>
            <thead>
              <tr><th>ID</th><th>Nome</th><th>Escopo</th><th>Status</th></tr>
            </thead>
            <tbody>${linhas}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  if (state.abaAtiva === "usuarios") {
    const linhas = state.usuarios
      .map(
        (u) => `
        <tr>
          <td>#${u.id_usuario}</td>
          <td><strong>${u.nome_usuario}</strong></td>
          <td>${u.email}</td>
          <td>${u.cidade ? `${u.cidade}/${u.uf}` : "-"}</td>
          <td>${u.tipo_plano || "-"}</td>
          <td><span class="badge ${u.tipo_usuario === "ADMIN" ? "badge-admin" : ""}">${u.tipo_usuario}</span></td>
        </tr>`
      )
      .join("");

    return `
      <div class="panel">
        <h2>Clientes e Usuários Registrados</h2>
        <div class="table-scroll-container">
          <table>
            <thead>
              <tr><th>ID</th><th>Nome</th><th>E-mail</th><th>Localização</th><th>Plano</th><th>Perfil</th></tr>
            </thead>
            <tbody>${linhas}</tbody>
          </table>
        </div>
      </div>
    `;
  }
}

function renderSubAbaCadastroProduto(state) {
  const editando = state.produtoEmEdicao;
  const categoriasPadrao = state.categorias.filter((c) => c.usuario_id === null);

  const opcoesCategorias = categoriasPadrao
    .map(
      (c) => `
      <option
        value="${c.id_categoria}"
        ${editando && editando.categoria_id === c.id_categoria ? "selected" : ""}
      >
        ${c.nome_categoria}
      </option>`
    )
    .join("");

  const unidades = [
    { valor: "Un", texto: "Unidade (Un)" },
    { valor: "Kg", texto: "Quilo (Kg)" },
    { valor: "L", texto: "Litro (L)" },
    { valor: "Cx", texto: "Caixa (Cx)" },
    { valor: "Pacote", texto: "Pacote" },
  ];

  const opcoesUnidades = unidades
    .map(
      (u) => `
      <option
        value="${u.valor}"
        ${editando && editando.unidade_medida_padrao === u.valor ? "selected" : ""}
      >
        ${u.texto}
      </option>`
    )
    .join("");

  return `
    <div class="subtab-card ${editando ? "form-editing" : ""}">
      <h3 class="subtab-title">
        ${
          editando
            ? `Alterar Dados do Produto #${editando.id_produto_global}`
            : "Novo Produto no Catálogo Global"
        }
      </h3>

      <form id="form-produto-global" class="cadastro-form-layout">
        <div class="form-group">
          <label for="campo-nome-oficial">Nome Oficial do Produto</label>
          <input
            type="text"
            id="campo-nome-oficial"
            name="nome_oficial"
            required
            minlength="2"
            maxlength="200"
            value="${escaparAtributo(editando?.nome_oficial)}"
            placeholder="Ex: Arroz Tipo 1 Camil 5kg"
          />
        </div>

        <div class="cadastro-row-3">
          <div class="form-group">
            <label for="campo-codigo-barras">Código de Barras (EAN)</label>
            <input
              type="text"
              id="campo-codigo-barras"
              name="codigo_barras"
              required
              minlength="1"
              maxlength="50"
              value="${escaparAtributo(editando?.codigo_barras)}"
              placeholder="7891000100103"
            />
          </div>

          <div class="form-group">
            <label for="campo-unidade">Unidade Padrão</label>
            <select id="campo-unidade" name="unidade_medida_padrao" required>
              ${opcoesUnidades}
            </select>
          </div>

          <div class="form-group">
            <label for="campo-categoria">Categoria Padrão</label>
            <select id="campo-categoria" name="categoria_id" required>
              ${opcoesCategorias}
            </select>
          </div>
        </div>

        <div class="cadastro-actions">
          <button type="submit" class="btn-orange">
            ${editando ? "Salvar Alterações" : "+ Incluir Produto"}
          </button>
          ${
            editando
              ? `<button type="button" id="btn-cancelar-edicao" class="btn-secondary">Cancelar Edição</button>`
              : ""
          }
        </div>
      </form>
    </div>
  `;
}

function renderSubAbaConsultaProduto(state) {
  const categoriasPadrao = state.categorias.filter((c) => c.usuario_id === null);
  const mapaCategorias = Object.fromEntries(
    state.categorias.map((c) => [c.id_categoria, c.nome_categoria])
  );

  const opcoesCategoriasFiltro = categoriasPadrao
    .map(
      (c) => `
      <option
        value="${c.id_categoria}"
        ${String(state.filtroCategoriaProduto) === String(c.id_categoria) ? "selected" : ""}
      >
        ${c.nome_categoria}
      </option>`
    )
    .join("");

  const linhas = state.produtosGlobais
    .map(
      (p) => `
      <tr>
        <td>#${p.id_produto_global}</td>
        <td><strong>${p.nome_oficial}</strong></td>
        <td>${p.codigo_barras}</td>
        <td>${p.unidade_medida_padrao}</td>
        <td>${p.categoria?.nome_categoria || mapaCategorias[p.categoria_id] || `Cat #${p.categoria_id}`}</td>
        <td>
          <div class="table-actions">
            <button type="button" class="btn-edit" data-edit-produto="${p.id_produto_global}">
              Editar
            </button>
            <button type="button" class="btn-danger" data-delete-produto="${p.id_produto_global}">
              Excluir
            </button>
          </div>
        </td>
      </tr>`
    )
    .join("");

  const total = state.totalProdutosGlobais;
  const limit = state.itensPorPaginaProdutos;
  const paginaAtual = state.paginaAtualProdutos;
  const totalPaginas = Math.max(1, Math.ceil(total / limit));
  const temFiltroAtivo = Boolean(state.filtroBuscaProduto || state.filtroCategoriaProduto);

  return `
    <form id="form-consulta-produtos" class="filter-bar">
      <div class="filter-search">
        <label for="input-filtro-busca">Nome ou Código de Barras (EAN)</label>
        <input
          type="search"
          id="input-filtro-busca"
          name="busca"
          value="${escaparAtributo(state.filtroBuscaProduto)}"
          placeholder="Digite o nome do produto ou código EAN..."
        />
      </div>

      <div class="filter-category">
        <label for="select-filtro-categoria">Categoria</label>
        <select id="select-filtro-categoria" name="categoria_id">
          <option value="">Todas as Categorias</option>
          ${opcoesCategoriasFiltro}
        </select>
      </div>

      <div class="filter-buttons">
        <button type="submit" class="btn-orange" ${state.buscandoProdutos ? "disabled" : ""}>
          ${state.buscandoProdutos ? "Buscando..." : "Consultar"}
        </button>
        ${
          temFiltroAtivo
            ? `<button type="button" id="btn-limpar-filtros" class="btn-secondary">
                Limpar
              </button>`
            : ""
        }
      </div>
    </form>

    <div class="table-scroll-container">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Produto</th>
            <th>EAN / Barras</th>
            <th>Unidade</th>
            <th>Categoria</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${
            state.buscandoProdutos
              ? `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Consultando catálogo global...</td></tr>`
              : linhas ||
                `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">Nenhum produto global encontrado para os filtros informados.</td></tr>`
          }
        </tbody>
      </table>
    </div>

    <div class="pagination-bar">
      <span class="pagination-info">
        Exibindo <strong>${state.produtosGlobais.length}</strong> de
        <strong>${formatarNumero(total)}</strong> produto(s)
      </span>
      <div class="pagination-controls">
        <button
          type="button"
          class="btn-secondary"
          data-page="${paginaAtual - 1}"
          ${paginaAtual <= 1 ? "disabled" : ""}
        >
          ← Anterior
        </button>
        <span class="pagination-page">
          Página <strong>${formatarNumero(paginaAtual)}</strong> de <strong>${formatarNumero(totalPaginas)}</strong>
        </span>
        <button
          type="button"
          class="btn-secondary"
          data-page="${paginaAtual + 1}"
          ${paginaAtual >= totalPaginas ? "disabled" : ""}
        >
          Próxima →
        </button>
      </div>
    </div>
  `;
}
// ─── HermesMed — Barra de navegação inferior ───
// Injetado em todas as páginas. Detecta a página atual pelo nome do arquivo,
// destaca o item ativo e abre a folha "Mais" com atalhos e ações.
(function () {
  'use strict';
  if (window.hermesmedNavbar) return; // evita duplicação
  window.hermesmedNavbar = true;

  // Os 4 atalhos principais + ações dentro da folha "Mais"
  const TABS = [
    { href: 'index.html',      icon: '🏠', label: 'Início' },
    { href: 'questoes.html',   icon: '📝', label: 'Questões' },
    { href: 'simulados.html',  icon: '📋', label: 'Simulados' },
    { href: 'desempenho.html', icon: '📊', label: 'Desempenho' },
    { kind: 'more',            icon: '•••', label: 'Mais' }
  ];

  const MORE_ITEMS = [
    { icon: '🎯', ico: '', name: 'Sessão de Estudo', sub: 'Personalizada por área e tópico', href: 'sessao.html' },
    { icon: '🃏', ico: 'blue', name: 'Flashcards', sub: 'Revisão rápida por decks', href: 'flashcard.html' },
    { icon: '🗓️', ico: 'green', name: 'Meu Plano', sub: 'Plano de estudos', href: 'plano.html' },
    { icon: '📈', ico: 'blue', name: 'Questões Rápidas', sub: 'Modo livre / prova', href: 'questoes.html' }
  ];

  function currentFile() {
    const p = location.pathname.split('/').pop().split('?')[0] || 'index.html';
    return p.toLowerCase();
  }

  function build() {
    const file = currentFile();
    const html = `
    <nav class="bottom-navbar" aria-label="Navegação principal">
      <div class="nav-inner">
        ${TABS.map(t => {
          if (t.kind === 'more') {
            return `<button type="button" class="nav-item" data-nav="more" aria-label="Mais opções">
              <span class="nav-icon">${t.icon}</span>
              <span>${t.label}</span><span class="nav-dot"></span>
            </button>`;
          }
          const active = file === t.href ? ' active' : '';
          return `<a href="${t.href}" class="nav-item${active}" data-nav="link" aria-label="${t.label}">
            <span class="nav-icon">${t.icon}</span>
            <span>${t.label}</span><span class="nav-dot"></span>
          </a>`;
        }).join('')}
      </div>
    </nav>

    <div class="more-overlay" id="moreOverlay" role="dialog" aria-modal="true" aria-label="Mais opções">
      <div class="more-sheet">
        <div class="more-handle"></div>
        <h3>Explorar</h3>
        ${MORE_ITEMS.map(m => `
          <a href="${m.href}" class="more-item">
            <span class="mi-icon ${m.ico}">${m.icon}</span>
            <span class="mi-tt"><span class="mi-name">${m.name}</span><br><span class="mi-sub">${m.sub}</span></span>
            <span class="mi-arrow">›</span>
          </a>
        `).join('')}
        <h3 style="margin-top:14px;">Ações</h3>
        <button type="button" class="more-item" data-act="tema">
          <span class="mi-icon">🌓</span>
          <span class="mi-tt"><span class="mi-name">Alternar tema</span><br><span class="mi-sub">Claro / escuro</span></span>
          <span class="mi-arrow">›</span>
        </button>
        <button type="button" class="more-item" data-act="sair">
          <span class="mi-icon red">🔒</span>
          <span class="mi-tt"><span class="mi-name">Sair</span><br><span class="mi-sub">Encerrar sessão</span></span>
          <span class="mi-arrow">›</span>
        </button>
      </div>
    </div>`;

    // Insere no fim do body
    const holder = document.createElement('div');
    holder.id = 'hermesmedNavbarRoot';
    holder.innerHTML = html.trim();
    document.body.appendChild(holder);

    const overlay = holder.querySelector('#moreOverlay');
    const moreBtn = holder.querySelector('[data-nav="more"]');

    function openSheet() { overlay.classList.add('open'); }
    function closeSheet() { overlay.classList.remove('open'); }

    moreBtn.addEventListener('click', openSheet);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeSheet(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

    // Ações
    const themeBtn = holder.querySelector('[data-act="tema"]');
    themeBtn.addEventListener('click', () => {
      if (window.hermesmedTema) window.hermesmedTema.toggle();
      else location.href = 'index.html';
      closeSheet();
    });
    const sairBtn = holder.querySelector('[data-act="sair"]');
    sairBtn.addEventListener('click', () => {
      try { localStorage.removeItem('hermesmed_auth'); } catch {}
      location.href = 'login.html?redirect=' + file;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }
})();
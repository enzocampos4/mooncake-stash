// ─── Tema claro/escuro HermesMed ───
// Salva a preferência no localStorage e aplica em todas as páginas.
(function () {
  const KEY = 'hermesmed_tema';

  function get() {
    try { return localStorage.getItem(KEY) || 'escuro'; }
    catch { return 'escuro'; }
  }
  function set(t) {
    try { localStorage.setItem(KEY, t); } catch {}
    aplicar(t);
  }
  function aplicar(t) {
    document.documentElement.setAttribute('data-tema', t);
  }
  function toggle() {
    set(get() === 'claro' ? 'escuro' : 'claro');
  }

  // Expõe globalmente
  window.hermesmedTema = {
    get, set, toggle, carregar: function () { window.requestAnimationFrame ? requestAnimationFrame(aplicar) : aplicar(get()); }
  };

  // Aplica logo no load (evita flash de tema errado)
  aplicar(get());
})();
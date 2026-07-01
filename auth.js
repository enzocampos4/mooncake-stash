// ─── Autenticação HermesMed ───
// Redireciona para login se não estiver autenticado
(function() {
  if (localStorage.getItem('hermesmed_auth') !== 'true') {
    // Preserva query params (ex: ?area=clinica-medica&modo=livre)
    const path = window.location.pathname.split('/').pop() || 'index.html';
    const qs = window.location.search || '';
    const redirect = path + qs;
    window.location.replace('login.html?redirect=' + encodeURIComponent(redirect));
  }
})();

// ─── Autenticação HermesMed ───
// Redireciona para login se não estiver autenticado
(function() {
  if (localStorage.getItem('hermesmed_auth') !== 'true') {
    const redirect = window.location.pathname.split('/').pop() || 'index.html';
    window.location.replace('login.html?redirect=' + encodeURIComponent(redirect));
  }
})();

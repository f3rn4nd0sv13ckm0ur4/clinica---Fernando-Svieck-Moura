// Modo escuro: lembra a escolha do usuário; se não houver, segue o tema do sistema.
(function () {
  var salvo = null;
  try { salvo = localStorage.getItem("tema"); } catch (e) {}
  var escuro = salvo ? salvo === "escuro" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  var raiz = document.documentElement;

  function aplicar(modoEscuro) {
    raiz.setAttribute("data-tema", modoEscuro ? "escuro" : "claro");
    var btn = document.getElementById("btn-tema");
    if (btn) btn.textContent = modoEscuro ? "☀️ Modo claro" : "🌙 Modo escuro";
  }

  aplicar(escuro); // aplica já no carregamento, evitando "piscar"

  document.addEventListener("DOMContentLoaded", function () {
    aplicar(escuro);
    document.getElementById("btn-tema").addEventListener("click", function () {
      escuro = !escuro;
      try { localStorage.setItem("tema", escuro ? "escuro" : "claro"); } catch (e) {}
      aplicar(escuro);
    });
  });
})();

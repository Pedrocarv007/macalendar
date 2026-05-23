/**
 * Splash screen — shows once per session.
 */
(function () {
  if (sessionStorage.getItem('splashShown')) return;

  const overlay = document.createElement('div');
  overlay.innerHTML = `
    <div style="position:fixed;inset:0;z-index:9999;background:#f0fdf4;display:flex;align-items:center;justify-content:center;flex-direction:column">
      <div style="width:64px;height:64px;border-radius:16px;background:linear-gradient(135deg,#00A651,#007a3d);display:flex;align-items:center;justify-content:center;margin-bottom:1.2rem;box-shadow:0 8px 24px rgba(0,166,81,.25)">
        <svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="16" y1="2" x2="16" y2="6"></line>
          <line x1="8" y1="2" x2="8" y2="6"></line>
          <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>
      </div>
      <h1 style="font-family:sans-serif;font-size:clamp(1.5rem,4vw,2.2rem);color:#15803d;letter-spacing:0.04em;font-weight:700;margin:0">
        Mac Calendar
      </h1>
      <p style="font-family:sans-serif;color:#6b7280;letter-spacing:0.25em;font-size:0.7rem;margin-top:0.4rem;text-transform:uppercase">TheCarv · Portal de Gestão</p>
      <div style="margin-top:1.8rem;display:flex;gap:6px">
        <span class="sdot"></span><span class="sdot sdot2"></span><span class="sdot sdot3"></span>
      </div>
    </div>
  `;

  const style = document.createElement('style');
  style.textContent = `
    .sdot { width:6px;height:6px;border-radius:50%;background:#00A651;animation:sdot 1.4s ease-in-out infinite; }
    .sdot2{animation-delay:0.2s;background:#FFCF00}
    .sdot3{animation-delay:0.4s}
    @keyframes sdot{0%,80%,100%{transform:scale(.6);opacity:.3}40%{transform:scale(1);opacity:1}}
  `;
  document.head.appendChild(style);
  document.body.appendChild(overlay);

  sessionStorage.setItem('splashShown', '1');

  setTimeout(() => {
    overlay.firstElementChild.style.opacity = '0';
    overlay.firstElementChild.style.transition = 'opacity 0.4s ease';
    setTimeout(() => overlay.remove(), 450);
  }, 2200);
})();

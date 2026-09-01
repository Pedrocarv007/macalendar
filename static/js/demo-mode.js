(function () {
  'use strict';

  const COOKIE = 'thecarv_demo_mode';
  const EXEMPT_NAME = 'pedro lopes campos de carvalho';
  const normalize = (value) => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('pt-PT');
  const enabled = () => document.cookie.split(';').some((part) => part.trim() === `${COOKIE}=1`);
  const exempt = (name) => normalize(name) === EXEMPT_NAME;

  function setCookie(active) {
    const value = active ? '1' : '0';
    const age = active ? 31536000 : 0;
    document.cookie = `${COOKIE}=${value}; Domain=.thecarv.com; Path=/; Max-Age=${age}; SameSite=Lax; Secure`;
    document.cookie = `${COOKIE}=${value}; Path=/; Max-Age=${age}; SameSite=Lax`;
  }

  function apply() {
    const active = enabled();
    document.documentElement.classList.toggle('demo-mode', active);
    document.querySelectorAll('[data-demo-person]').forEach((element) => {
      const name = normalize(element.dataset.demoPerson);
      element.classList.toggle('demo-person-private', Boolean(name) && !exempt(name));
    });
    document.querySelectorAll('[data-demo-toggle]').forEach((button) => {
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
      button.title = active ? 'Desativar modo demo' : 'Ativar modo demo';
      const label = button.querySelector('[data-demo-label]');
      const text = active ? 'Demo ativo' : 'Ativar demo';
      if (label && label.textContent !== text) label.textContent = text;
    });
  }

  document.addEventListener('click', (event) => {
    if (!event.target.closest('[data-demo-toggle]')) return;
    setCookie(!enabled());
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    new MutationObserver(apply).observe(document.body, { childList: true, subtree: true });
  });
  window.addEventListener('pageshow', apply);
  window.TheCarvDemo = { refresh: apply };
})();

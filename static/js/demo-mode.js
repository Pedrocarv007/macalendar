(function () {
  'use strict';

  const COOKIE = 'thecarv_demo_mode';
  const EXEMPT_NAME = 'pedro lopes campos de carvalho';
  const normalize = (value) => String(value || '').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLocaleLowerCase('pt-PT');
  const enabled = () => document.cookie.split(';').some((part) => part.trim() === `${COOKIE}=1`);
  const exempt = (name) => normalize(name) === EXEMPT_NAME;

  function apply() {
    const active = enabled();
    document.documentElement.classList.toggle('demo-mode', active);
    document.querySelectorAll('[data-demo-person]').forEach((element) => {
      const name = normalize(element.dataset.demoPerson);
      element.classList.toggle('demo-person-private', !exempt(name));
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    apply();
    new MutationObserver(apply).observe(document.body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['data-demo-person'],
    });
  });
  window.addEventListener('pageshow', apply);
  window.TheCarvDemo = { refresh: apply };
})();

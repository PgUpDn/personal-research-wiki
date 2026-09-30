/* Shared enhancements. All page content and navigation remain available offline. */
(() => {
  'use strict';
  const toggle = document.querySelector('.mobile-toggle');
  const sidebar = document.querySelector('.workspace-sidebar');
  const scrim = document.querySelector('.nav-scrim');
  const mobile = window.matchMedia('(max-width: 900px)');
  const setNavigation = (open, restoreFocus = false) => {
    document.body.classList.toggle('nav-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
    toggle?.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    if (sidebar) sidebar.inert = mobile.matches && !open;
    if (open) sidebar?.querySelector('a')?.focus();
    else if (restoreFocus) toggle?.focus();
  };
  toggle?.addEventListener('click', () => setNavigation(!document.body.classList.contains('nav-open'), true));
  scrim?.addEventListener('click', () => setNavigation(false, true));
  sidebar?.addEventListener('click', event => {
    if (event.target.closest('a') && mobile.matches) setNavigation(false);
  });
  mobile.addEventListener('change', () => setNavigation(false));
  setNavigation(false);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setNavigation(false, document.body.classList.contains('nav-open'));
    if (event.key === 'Tab' && mobile.matches && document.body.classList.contains('nav-open')) {
      const focusable = [...sidebar.querySelectorAll('a,button')];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    const editing = event.target.closest('input,textarea,select,[contenteditable="true"]');
    if (event.key === '/' && !editing && !event.metaKey && !event.ctrlKey && !event.altKey) {
      if (document.querySelector('[data-search-input]')) return;
      event.preventDefault();
      document.querySelector('.topbar-search')?.click();
    }
  });
  const tocLinks = [...document.querySelectorAll('.toc-links a')];
  if (tocLinks.length) {
    const headings = tocLinks.map(link => document.getElementById(decodeURIComponent(link.hash.slice(1))));
    let frame = 0;
    const updateToc = () => {
      frame = 0;
      let selected = 0;
      headings.forEach((heading, index) => { if (heading && heading.getBoundingClientRect().top <= 150) selected = index; });
      tocLinks.forEach((link, index) => {
        link.classList.toggle('active', index === selected);
        if (index === selected) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    };
    document.addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(updateToc); }, { passive: true });
    updateToc();
  }
  document.querySelectorAll('[data-question]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.querySelector('[data-ask-input]');
      input.value = button.dataset.question;
      input.focus();
    });
  });
  document.querySelector('[data-ask-input]')?.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      if (!document.querySelector('[data-ask-submit]').disabled) document.querySelector('[data-ask-form]').requestSubmit();
    }
  });

  // Create elements from a small Markdown subset; never interpret answer HTML.
  const inline = (parent, source) => {
    const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[\[[^\]]+\]\]|\[[^\]]+\]\([^\s)]+\))/g;
    let offset = 0;
    for (const match of source.matchAll(pattern)) {
      parent.append(document.createTextNode(source.slice(offset, match.index)));
      const token = match[0];
      let element;
      if (token.startsWith('`')) { element = document.createElement('code'); element.textContent = token.slice(1, -1); }
      else if (token.startsWith('**')) { element = document.createElement('strong'); element.textContent = token.slice(2, -2); }
      else if (token.startsWith('[[')) {
        const [target, label] = token.slice(2, -2).split('|');
        element = document.createElement('a'); element.textContent = label || target;
        element.href = `search.html?q=${encodeURIComponent(target)}`;
      } else {
        const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
        element = document.createElement('span'); element.textContent = link[1];
        try {
          const url = new URL(link[2], window.location.href);
          if (['https:', 'http:'].includes(url.protocol) || (url.protocol === 'file:' && !/^[a-z][a-z\d+.-]*:/i.test(link[2]))) {
            element = document.createElement('a'); element.textContent = link[1]; element.href = url.href;
            if (url.origin !== window.location.origin) { element.target = '_blank'; element.rel = 'noopener noreferrer'; }
          }
        } catch (_) { /* Invalid links remain readable text. */ }
      }
      parent.append(element); offset = match.index + token.length;
    }
    parent.append(document.createTextNode(source.slice(offset)));
  };
  const renderAnswer = (container, text) => {
    const fragment = document.createDocumentFragment();
    const lines = String(text).split('\n');
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) { index++; continue; }
      if (line.trim().startsWith('```')) {
        const code = []; index++;
        while (index < lines.length && !lines[index].trim().startsWith('```')) code.push(lines[index++]);
        index++;
        const pre = document.createElement('pre'); const element = document.createElement('code');
        element.textContent = code.join('\n'); pre.append(element); fragment.append(pre); continue;
      }
      const heading = /^(#{1,6})\s+(.*)$/.exec(line);
      if (heading) {
        const element = document.createElement(`h${Math.min(heading[1].length + 1, 6)}`);
        inline(element, heading[2]); fragment.append(element); index++; continue;
      }
      const list = /^\s*(?:[-*]|\d+\.)\s+/.exec(line);
      if (list) {
        const levels = [];
        while (index < lines.length) {
          const match = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(lines[index]);
          if (!match) break;
          const indent = match[1].replace(/\t/g, '    ').length;
          const tag = /\d/.test(match[2]) ? 'ol' : 'ul';
          while (levels.length && levels[levels.length - 1].indent > indent) levels.pop();
          if (levels.length && levels[levels.length - 1].indent === indent && levels[levels.length - 1].tag !== tag) levels.pop();
          if (!levels.length || levels[levels.length - 1].indent < indent) {
            const element = document.createElement(tag);
            if (tag === 'ol') element.start = parseInt(match[2], 10);
            const parent = levels.length ? levels[levels.length - 1].lastItem : fragment;
            parent.append(element);
            levels.push({ indent, tag, element, lastItem: null });
          }
          const level = levels[levels.length - 1];
          const item = document.createElement('li'); inline(item, match[3]); level.element.append(item); level.lastItem = item;
          index++;
        }
        continue;
      }
      if (line.includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1] || '')) {
        const wrapper = document.createElement('div'); wrapper.className = 'table-scroll'; wrapper.tabIndex = 0;
        const table = document.createElement('table'); const header = document.createElement('thead');
        const row = (value, tag) => {
          const tr = document.createElement('tr');
          const cells = []; let cell = ''; let codeFence = ''; let wikiDepth = 0;
          const valueText = value.trim();
          for (let i = 0; i < valueText.length; i++) {
            const char = valueText[i];
            if (char === '\\' && i + 1 < valueText.length) { cell += valueText[++i]; continue; }
            if (char === '`') {
              const fence = /^`+/.exec(valueText.slice(i))[0];
              if (!codeFence) codeFence = fence; else if (codeFence === fence) codeFence = '';
              cell += fence; i += fence.length - 1; continue;
            }
            if (!codeFence && valueText.slice(i, i + 2) === '[[') { wikiDepth++; cell += '[['; i++; continue; }
            if (!codeFence && valueText.slice(i, i + 2) === ']]') { wikiDepth = Math.max(0, wikiDepth - 1); cell += ']]'; i++; continue; }
            if (char === '|' && !codeFence && !wikiDepth) { cells.push(cell); cell = ''; } else cell += char;
          }
          cells.push(cell);
          if (!cells[0].trim()) cells.shift();
          if (!cells[cells.length - 1]?.trim()) cells.pop();
          cells.forEach(cell => { const td = document.createElement(tag); inline(td, cell.trim()); tr.append(td); });
          return tr;
        };
        header.append(row(line, 'th')); table.append(header); index += 2;
        const body = document.createElement('tbody');
        while (index < lines.length && lines[index].includes('|') && lines[index].trim()) body.append(row(lines[index++], 'td'));
        table.append(body); wrapper.append(table); fragment.append(wrapper); continue;
      }
      const paragraph = document.createElement('p'); inline(paragraph, line); fragment.append(paragraph); index++;
    }
    container.replaceChildren(fragment);
  };
  window.WikiUI = { renderAnswer };
})();

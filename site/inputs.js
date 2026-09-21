/* Native suggestion menus: typing remains available, and choices never save. */
(() => {
  'use strict';
  const fold = (value) => value.toLowerCase().replace(/\//g, '').replace(/\s+/g, ' ').trim();
  const choice = (value, label = value) => ({ value: String(value), label });
  function matching(options, query) {
    const key = fold(query);
    return options.filter((item) => fold(item.label).includes(key));
  }
  function insertTemplate(current, template, multiline = false) {
    return current.trim() ? `${current.trim()}${multiline ? '\n' : ' '}${template}` : template;
  }
  function hasPrompts(value) { return /\[[^\]]+\]/.test(value); }
  function dateChoices({ today, selected, start, optional = false, month = false }) {
    const options = [];
    const add = (day, label) => { if (day) options.push(choice(month ? day.slice(0, 7) : day, `${label} · ${month ? day.slice(0, 7) : day}`)); };
    if (optional) options.push(choice('', 'Any date · clear this limit'));
    if (start) {
      add(start, 'Same as From');
      for (const [days, label] of [[6, '7-day stay'], [29, '30-day stay']]) {
        const date = new Date(`${start}T00:00:00Z`);
        date.setUTCDate(date.getUTCDate() + days);
        add(date.toISOString().slice(0, 10), `${label} · inclusive`);
      }
    }
    add(today, 'Today');
    add(selected, 'Selected schedule date');
    add('2017-07-12', 'Sample history');
    add('2010-07-29', 'Fit example');
    return options;
  }
  function lengthChoices(vessel) {
    return [choice('', 'Unknown · clear measurement'),
      ...(vessel?.length_ft > 0 ? [choice(vessel.length_ft, `Recorded for this vessel · ${vessel.length_ft} ft`)] : [])];
  }

  function attach(input, { label, options, searchable = false, template = false, onLoad, onChoose, help = '' }) {
    const wrapper = document.createElement('div');
    wrapper.className = 'input-assist';
    const fieldLabel = input.closest('label');
    const original = fieldLabel || input;
    if (fieldLabel) {
      wrapper.className += ` ${fieldLabel.className}`;
      wrapper.hidden = fieldLabel.hidden;
      fieldLabel.hidden = false;
      fieldLabel.className = '';
      if (fieldLabel.id) { wrapper.id = fieldLabel.id; fieldLabel.removeAttribute('id'); }
      fieldLabel.htmlFor = input.id;
    }
    original.replaceWith(wrapper);
    wrapper.append(original);
    const menu = document.createElement('select');
    menu.id = `${input.id}-choices`;
    menu.className = 'input-choices';
    menu.setAttribute('aria-label', `${label} suggestions`);
    menu.setAttribute('aria-controls', input.id);
    const status = document.createElement('span');
    status.id = `${input.id}-choice-status`;
    status.className = 'choice-status';
    status.setAttribute('role', 'status');
    menu.setAttribute('aria-describedby', status.id);
    wrapper.append(menu, status);
    let items = [], sequence = 0, timer, usingTemplate = false, choosing = false;
    const placeholder = () => new Option(template ? 'Add a template…' : 'Choose a suggestion…', '');
    async function refresh() {
      clearTimeout(timer);
      const seq = ++sequence;
      const query = searchable ? input.value : '';
      if (!items.length) { menu.replaceChildren(placeholder()); menu.disabled = true; }
      status.textContent = 'Loading suggestions…';
      try {
        const pending = options(query);
        const result = pending && typeof pending.then === 'function' ? await pending : pending;
        if (seq !== sequence || !input.isConnected) return;
        items = result;
        menu.replaceChildren(placeholder(), ...items.map((item, index) => new Option(item.label, String(index))));
        menu.disabled = input.disabled || !items.length;
        status.textContent = items.length ? (help || (searchable ? `${items.length === 1000 ? 'First 1,000' : items.length} suggestion${items.length === 1 ? '' : 's'}. Type to narrow the list.` : 'Or enter your own value.'))
          : 'No matches. You can still type your own value.';
        if (onLoad) onLoad(items);
      } catch (_) {
        if (seq !== sequence) return;
        status.textContent = 'Suggestions unavailable. Keep typing, or focus this field to retry.';
        items = [];
        menu.replaceChildren(placeholder());
        menu.disabled = true;
        // A failed lookup never supplies stale choices or concludes a vessel is new.
      }
    }
    menu.addEventListener('input', (ev) => ev.stopPropagation());
    menu.addEventListener('blur', () => { menu.value = ''; });
    menu.addEventListener('change', (ev) => {
      ev.stopPropagation();
      if (menu.value === '' || input.disabled) return;
      const item = items[Number(menu.value)];
      if (!item) return;
      ++sequence;
      clearTimeout(timer);
      if (onChoose) onChoose(item);
      input.value = template ? insertTemplate(input.value, item.value, input.tagName === 'TEXTAREA') : item.value;
      usingTemplate ||= template;
      choosing = true;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      choosing = false;
      if (template) {
        menu.value = '';
        input.focus();
        const prompt = /\[[^\]]+\]/.exec(input.value);
        if (prompt) input.setSelectionRange(prompt.index, prompt.index + prompt[0].length);
      }
    });
    input.addEventListener('input', () => {
      input.setCustomValidity(usingTemplate && hasPrompts(input.value) ? 'Replace the bracketed template prompts with your details, or remove them.' : '');
      // Keep native menus focused and stable while arrow keys move through choices.
      if (!searchable || choosing) return;
      ++sequence; // Ignore a slow response as soon as the query changes.
      clearTimeout(timer);
      menu.disabled = true;
      status.textContent = 'Finding suggestions…';
      timer = setTimeout(refresh, 150);
    });
    input.addEventListener('focus', refresh);
    menu.addEventListener('focus', () => { if (!searchable) refresh(); });
    // Keep companion controls disabled during the existing save/review locks.
    new MutationObserver(() => { menu.disabled = input.disabled || !items.length; })
      .observe(input, { attributes: true, attributeFilter: ['disabled'] });
    refresh();
    return { refresh };
  }
  const api = { attach, choice, matching, insertTemplate, hasPrompts, dateChoices, lengthChoices };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else window.InputChoices = api;
})();

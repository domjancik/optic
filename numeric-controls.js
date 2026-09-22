/** Small, dependency-free number-field enhancements for plain HTML forms. */
export function clamp(value, min = -Infinity, max = Infinity) {
  return Math.min(max, Math.max(min, value));
}

export function decimalPlaces(value) {
  const text = String(value ?? '');
  const exponent = text.match(/e-(\d+)$/i);
  if (exponent) return Number(exponent[1]);
  const dot = text.indexOf('.');
  return dot < 0 ? 0 : text.length - dot - 1;
}

export function stepNumericValue(value, step, direction, min = -Infinity, max = Infinity, modifiers = {}) {
  const base = Number.isFinite(Number(value)) ? Number(value) : 0;
  const unit = Number.isFinite(Number(step)) && Number(step) > 0 ? Number(step) : 1;
  const multiplier = modifiers.ctrlKey || modifiers.metaKey ? 10 : modifiers.shiftKey ? .1 : 1;
  const precision = Math.min(12, decimalPlaces(unit) + (multiplier === .1 ? 1 : 0));
  return Number(clamp(base + unit * direction * multiplier, min, max).toFixed(precision));
}

function numericBounds(input) {
  return {
    min: input.min === '' ? -Infinity : Number(input.min),
    max: input.max === '' ? Infinity : Number(input.max),
    step: input.step === 'any' || input.step === '' ? 1 : Number(input.step)
  };
}

function emit(input, type) {
  input.dispatchEvent(new Event(type, { bubbles: true }));
}

function update(input, value, commit = false) {
  input.value = String(value);
  emit(input, 'input');
  if (commit) emit(input, 'change');
}

function dragHandle(input) {
  const label=input.closest('.control')?.querySelector('label') || input.closest('label');
  if(label)return label;
  const grip=document.createElement('span');grip.textContent='↔';grip.className='number-grip';
  input.before(grip);return grip;
}

/**
 * Adds compact mouse/touch drag and guarded wheel control to numeric inputs.
 * Existing input/change listeners remain the source of truth because mutations
 * dispatch ordinary bubbling events.
 */
export function attachNumericControls(root = document, { onInput, onCommit } = {}) {
  const cleanups = [];
  for (const input of root.querySelectorAll('input[type="number"]')) {
    if (input.dataset.numericControlsAttached) continue;
    input.dataset.numericControlsAttached = 'true';
    const inputListener = () => onInput?.({ input, value: input.valueAsNumber });
    const commitListener = () => onCommit?.({ input, value: input.valueAsNumber });
    input.addEventListener('input', inputListener);
    input.addEventListener('change', commitListener);

    const wheel = event => {
      if (document.activeElement !== input && !input.matches(':hover')) return;
      event.preventDefault();
      const { min, max, step } = numericBounds(input);
      update(input, stepNumericValue(input.value, step, event.deltaY < 0 ? 1 : -1, min, max, event), true);
    };
    input.addEventListener('wheel', wheel, { passive: false });

    const handle = dragHandle(input);
    if (handle) {
      handle.classList.add('numeric-drag-handle');
      handle.title = `${handle.textContent.trim()} — drag horizontally; Shift fine, Ctrl coarse`;
      const pointerDown = event => {
        if (event.button !== 0 || event.target.closest('input,select,button')) return;
        event.preventDefault();input.dataset.numericDragging='true';
        const originX = event.clientX, origin = Number.isFinite(input.valueAsNumber) ? input.valueAsNumber : 0;
        let changed = false;
        const move = moveEvent => {
          const pixels = Math.trunc((moveEvent.clientX - originX) / 8);
          const { min, max, step } = numericBounds(input);
          const value = stepNumericValue(origin, step, pixels, min, max, moveEvent);
          if (value !== input.valueAsNumber) { changed = true; update(input, value); }
        };
        const up = () => {
          window.removeEventListener('pointermove', move);
          window.removeEventListener('pointercancel', up);
          if (changed) emit(input, 'change');
          delete input.dataset.numericDragging;
        };
        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', up, { once: true });
        window.addEventListener('pointercancel', up, { once: true });
      };
      handle.addEventListener('pointerdown', pointerDown);
      cleanups.push(() => handle.removeEventListener('pointerdown', pointerDown));
    }
    cleanups.push(() => {
      delete input.dataset.numericControlsAttached;
      input.removeEventListener('input', inputListener);
      input.removeEventListener('change', commitListener);
      input.removeEventListener('wheel', wheel);
    });
  }
  return () => cleanups.forEach(cleanup => cleanup());
}

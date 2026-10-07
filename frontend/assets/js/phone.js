export function formatBrazilianPhone(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 11);
  if (!digits) return '';
  if (digits.length <= 2) return `(${digits}`;

  const ddd = `(${digits.slice(0, 2)}) `;
  const localNumber = digits.slice(2);
  const prefixLength = digits.length > 10 ? 5 : 4;
  if (localNumber.length <= prefixLength) return ddd + localNumber;
  return `${ddd}${localNumber.slice(0, prefixLength)}-${localNumber.slice(prefixLength)}`;
}

export function formatBrazilianCnpj(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 14);
  if (!digits) return '';
  let formatted = digits.slice(0, 2);
  if (digits.length > 2) formatted += `.${digits.slice(2, 5)}`;
  if (digits.length > 5) formatted += `.${digits.slice(5, 8)}`;
  if (digits.length > 8) formatted += `/${digits.slice(8, 12)}`;
  if (digits.length > 12) formatted += `-${digits.slice(12, 14)}`;
  return formatted;
}

function formatInputValue(input, formatter) {
  const digitCountBeforeCursor = input.value
    .slice(0, input.selectionStart ?? input.value.length)
    .replace(/\D/g, '').length;
  const formatted = formatter(input.value);
  if (formatted === input.value) return;

  input.value = formatted;
  if (typeof input.setSelectionRange !== 'function') return;
  if (digitCountBeforeCursor === 0) {
    input.setSelectionRange(0, 0);
    return;
  }
  let digitsSeen = 0;
  let cursorPosition = 0;
  for (let index = 0; index < formatted.length; index += 1) {
    if (/\d/.test(formatted[index])) digitsSeen += 1;
    cursorPosition = index + 1;
    if (digitsSeen >= digitCountBeforeCursor) break;
  }
  input.setSelectionRange(cursorPosition, cursorPosition);
}

export function initializePhoneInputs() {
  document.querySelectorAll('input[type="tel"]').forEach((input) => {
    if (input.value) input.value = formatBrazilianPhone(input.value);
  });

  document.addEventListener('input', (event) => {
    const input = event.target.closest('input[type="tel"]');
    if (!input) return;
    formatInputValue(input, formatBrazilianPhone);
  });
}

export function initializeCnpjInputs() {
  document.querySelectorAll('input[name="cnpj"], input[data-edit-field="cnpj"]').forEach((input) => {
    if (input.value) input.value = formatBrazilianCnpj(input.value);
  });

  document.addEventListener('input', (event) => {
    const input = event.target.closest('input[name="cnpj"], input[data-edit-field="cnpj"]');
    if (!input) return;
    formatInputValue(input, formatBrazilianCnpj);
  });
}

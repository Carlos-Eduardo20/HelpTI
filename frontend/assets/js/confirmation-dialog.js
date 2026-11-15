export function confirmarExclusao(entidade) {
  let dialog = document.getElementById('confirmarExclusaoDialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.id = 'confirmarExclusaoDialog';
    dialog.className = 'confirmation-dialog';
    dialog.setAttribute('aria-labelledby', 'confirmarExclusaoTexto');
    document.body.append(dialog);
  }
  dialog.innerHTML = `
    <form method="dialog" class="confirmation-dialog__content">
      <p id="confirmarExclusaoTexto"></p>
      <div class="confirmation-dialog__actions">
        <button type="submit" class="button button--secondary" value="cancel">Cancelar</button>
        <button type="submit" class="confirmation-dialog__delete" value="delete">Excluir</button>
      </div>
    </form>`;
  dialog.querySelector('#confirmarExclusaoTexto').textContent =
    `Você tem certeza que deseja excluir ${entidade}?`;
  return new Promise((resolve) => {
    dialog.addEventListener('close', () => resolve(dialog.returnValue === 'delete'), { once: true });
    dialog.showModal();
  });
}

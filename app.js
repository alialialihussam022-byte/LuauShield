const source = document.querySelector('#source');
const output = document.querySelector('#output');
const status = document.querySelector('#status');
const button = document.querySelector('#obfuscate');
const setStatus = (text, kind='idle') => { status.className = `status ${kind}`; status.querySelector('span:last-child').textContent = text; };
button.addEventListener('click', async () => {
  button.disabled = true; setStatus('Checking syntax and transforming safe literals…');
  try {
    const seed = document.querySelector('#seed').value;
    const response = await fetch('/api/obfuscate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source:source.value, mode:document.querySelector('#mode').value, seed:seed ? Number(seed) : null})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Obfuscation failed.');
    output.value = data.code;
    setStatus(`Success · ${data.changed} string literal${data.changed === 1 ? '' : 's'} transformed · all other source preserved.`, 'ok');
  } catch (error) { output.value = ''; setStatus(error.message, 'error'); }
  finally { button.disabled = false; }
});
document.querySelector('#copy').addEventListener('click', async () => { if (!output.value) return setStatus('Nothing to copy yet.'); await navigator.clipboard.writeText(output.value); setStatus('Protected output copied to clipboard.', 'ok'); });
document.querySelector('#clear').addEventListener('click', () => { source.value=''; output.value=''; setStatus('Ready. Output is never generated when validation fails.'); source.focus(); });
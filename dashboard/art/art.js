'use strict';
const canonical = document.querySelector('link[rel="canonical"]').href;
const status = document.getElementById('share-status');
let statusTimer;
function announce(message) { clearTimeout(statusTimer); status.textContent = message; statusTimer = setTimeout(() => { status.textContent = ''; }, 5000); }
async function sharePiece(button) {
  const id = button.dataset.share;
  const url = new URL(canonical);
  if (id) url.hash = id;
  const title = button.dataset.title ? `${button.dataset.title} · Bounded Light Speed` : 'Bounded Light Speed · LumenCore';
  button.disabled = true;
  try {
    if (navigator.share) {
      try { await navigator.share({title, text:'Created by Robert Ashworth using AI tools. Explore the collection.', url:url.href}); return; }
      catch (error) { if (error.name === 'AbortError') return; }
    }
    if (navigator.clipboard?.writeText) {
      try { await navigator.clipboard.writeText(url.href); announce('Link copied. Share it wherever your people are.'); return; } catch {}
    }
    const fallback = document.getElementById('copy-fallback');
    fallback.hidden = false;
    const input = document.getElementById('share-url'); input.value = url.href; input.focus(); input.select();
  } finally { button.disabled = false; }
}
document.querySelectorAll('[data-share]').forEach(button => button.addEventListener('click', () => sharePiece(button)));
document.getElementById('close-copy').addEventListener('click', () => { document.getElementById('copy-fallback').hidden = true; });

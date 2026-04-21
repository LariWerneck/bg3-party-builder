const API = 'https://csicwu75lc.execute-api.us-east-2.amazonaws.com/dev';

const STYLES = {
  hero:     { label: 'The Hero',     desc: 'Justice, honor, protect the innocent' },
  villain:  { label: 'The Villain',  desc: 'Power, cruelty, self above all' },
  rogue:    { label: 'The Rogue',    desc: 'Stealth, deception, personal gain' },
  scholar:  { label: 'The Scholar',  desc: 'Magic, knowledge, careful choices' },
  warrior:  { label: 'The Warrior',  desc: 'Strength, combat, direct action' },
  diplomat: { label: 'The Diplomat', desc: 'Peace, persuasion, compassion' },
};

let activeStyle = null;

function initGrid() {
  const grid = document.getElementById('styleGrid');
  Object.entries(STYLES).forEach(([id, s]) => {
    const btn = document.createElement('button');
    btn.className = 'style-btn';
    btn.dataset.id = id;
    btn.innerHTML = `
      <span class="style-btn-name">${s.label}</span>
      <span class="style-btn-desc">${s.desc}</span>
    `;
    btn.addEventListener('click', () => selectStyle(id));
    grid.appendChild(btn);
  });
}

function selectStyle(id) {
  activeStyle = id;
  document.querySelectorAll('.style-btn')
    .forEach(b => b.classList.toggle('active', b.dataset.id === id));
  document.getElementById('customInput').value = '';
  buildParty(id);
}

async function buildParty(override) {
  const style = override
    || document.getElementById('customInput').value.trim()
    || activeStyle;

  if (!style) return;

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  document.getElementById('result').innerHTML =
    '<div class="loading">Consulting the stars</div>';

  try {
    const res = await fetch(`${API}/party?style=${encodeURIComponent(style)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    renderResult(await res.json());
  } catch (e) {
    document.getElementById('result').innerHTML =
      '<div class="error-msg">The oracle is unavailable. Try again shortly.</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderResult(data) {
  const { playstyle: ps, party = [], avoid = [] } = data;

  let html = `
    <div class="playstyle-banner">
      <div class="ps-label">Detected playstyle</div>
      <div class="ps-name">${ps.label}</div>
      <div class="ps-desc">${ps.description}</div>
    </div>
    <div class="party-title">Your ideal party</div>
  `;

  party.forEach((c, i) => {
    const acts = (c.top_approved || []).slice(0, 2);
    const sign = c.compatibility_score >= 0 ? '+' : '';
    const roman = ['I', 'II', 'III'][i] || String(i + 1);

    html += `
      <div class="companion-card">
        <div class="c-rank">${roman}</div>
        <div class="c-body">
          <div class="c-name">${c.name}</div>
          <div class="c-class">${c.class} &middot; ${c.race}</div>
          <div class="c-why">${trunc(c.why, 120)}</div>
          ${acts.length ? `
            <div class="c-actions">
              ${acts.map(a => `
                <span class="action-pill">
                  <span class="val">+${a.value}</span>
                  ${trunc(a.action, 55)}
                </span>
              `).join('')}
            </div>
          ` : ''}
        </div>
        <div class="c-score">
          <div class="score-num">${sign}${c.compatibility_score}</div>
          <div class="score-lbl">score</div>
        </div>
      </div>
    `;
  });

  if (avoid.length) {
    html += `<div class="party-title" style="margin-top:2.5rem">Companions to avoid</div>`;
    avoid.forEach(c => {
      html += `
        <div class="avoid-card">
          <div>
            <div class="avoid-name">${c.name}</div>
            <div class="avoid-why">${c.why}</div>
          </div>
          <div class="avoid-score">${c.score}</div>
        </div>
      `;
    });
  }

  document.getElementById('result').innerHTML = html;
}

function trunc(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n).trimEnd() + '…' : str;
}

document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  document.getElementById('searchBtn')
    .addEventListener('click', () => buildParty());
});
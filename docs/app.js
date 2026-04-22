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
  setResult('<div class="loading">Consulting the stars</div>');

  try {
    const res = await fetch(`${API}/party?style=${encodeURIComponent(style)}`);
    if (!res.ok) throw new Error();
    renderParty(await res.json());
  } catch {
    setResult('<div class="error-msg">The oracle is unavailable. Try again shortly.</div>');
  } finally {
    btn.disabled = false;
  }
}

async function showCompanion(name) {
  setResult('<div class="loading">Summoning ' + name + '</div>');
  try {
    const res = await fetch(`${API}/companion?name=${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error();
    renderCompanion(await res.json());
  } catch {
    setResult('<div class="error-msg">Could not reach the companion.</div>');
  }
}

function renderParty(data) {
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
          <div class="c-name">
            <button class="name-link" onclick="showCompanion('${c.name}')">${c.name}</button>
          </div>
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

  setResult(html);
}

function renderCompanion(c) {
  const thresholds = c.approval_thresholds || {};

  const bar = (val) => {
    const pct = Math.round(((val + 50) / 150) * 100);
    return `<div class="approval-track"><div class="approval-fill" style="width:${pct}%"></div></div>`;
  };

  let html = `
    <button class="back-btn" onclick="history.back(); renderLastParty()">
      &larr; Back to party
    </button>

    <div class="companion-detail-header">
      <div class="cd-name">${c.name}</div>
      <div class="cd-meta">${c.class} (${c.subclass}) &middot; ${c.race}</div>
      <a class="cd-wiki" href="${c.url}" target="_blank">View on bg3.wiki &rarr;</a>
    </div>

    <div class="cd-grid">
      <div class="cd-section">
        <div class="cd-section-title">Approves of</div>
        ${(c.likes || []).map(l => `<div class="tag tag-pos">${l}</div>`).join('')}
      </div>
      <div class="cd-section">
        <div class="cd-section-title">Disapproves of</div>
        ${(c.dislikes || []).map(d => `<div class="tag tag-neg">${d}</div>`).join('')}
      </div>
    </div>

    <div class="cd-section-title" style="margin-top:1.5rem">Top approved actions <span class="events-count">${c.total_events} events total</span></div>
    ${(c.top_approved || []).map(e => `
      <div class="event-row event-pos">
        <span class="event-val">+${e.value}</span>
        <span class="event-action">${e.action}</span>
      </div>
    `).join('')}

    <div class="cd-section-title" style="margin-top:1.2rem">Top disapproved actions</div>
    ${(c.top_disapproved || []).map(e => `
      <div class="event-row event-neg">
        <span class="event-val">${e.value}</span>
        <span class="event-action">${e.action}</span>
      </div>
    `).join('')}

    <div class="cd-section-title" style="margin-top:1.5rem">Approval thresholds</div>
    <div class="threshold-list">
      ${Object.entries(thresholds).map(([k, v]) => `
        <div class="threshold-row">
          <span class="threshold-label">${k.replace(/_/g, ' ')}</span>
          <span class="threshold-val ${v >= 0 ? 'pos' : 'neg'}">${v >= 0 ? '+' : ''}${v}</span>
        </div>
      `).join('')}
    </div>
  `;

  setResult(html);
}

let _lastPartyHTML = '';
function setResult(html) {
  document.getElementById('result').innerHTML = html;
}

function trunc(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n).trimEnd() + '…' : str;
}

document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  document.getElementById('searchBtn').addEventListener('click', () => buildParty());
  document.getElementById('customInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') buildParty();
  });
});
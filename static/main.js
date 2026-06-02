// ================================================================
// SKILFORGE — main.js  |  Premium Interactions Engine
// ================================================================

// ── 1. CURSOR GLOW ───────────────────────────────────────────────
const glowEl = document.createElement('div');
glowEl.className = 'cursor-glow';
document.body.appendChild(glowEl);

let mouseX = 0, mouseY = 0, glowX = 0, glowY = 0;
document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

(function animateGlow() {
  glowX += (mouseX - glowX) * 0.08;
  glowY += (mouseY - glowY) * 0.08;
  glowEl.style.left = glowX + 'px';
  glowEl.style.top  = glowY + 'px';
  requestAnimationFrame(animateGlow);
})();


// ── 2. NAVBAR SCROLL EFFECT ──────────────────────────────────────
const nav = document.querySelector('.sf-nav');
if (nav) {
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });
}


// ── 3. COUNT-UP ANIMATION ────────────────────────────────────────
function countUp(el) {
  const target   = parseInt(el.getAttribute('data-count')) || 0;
  const duration = 1400;
  const start    = performance.now();
  function update(now) {
    const p = Math.min((now - start) / duration, 1);
    const e = 1 - Math.pow(1 - p, 4);
    el.textContent = Math.floor(e * target).toLocaleString();
    if (p < 1) requestAnimationFrame(update);
    else el.textContent = target.toLocaleString();
  }
  requestAnimationFrame(update);
}

const countObs = new IntersectionObserver(entries => {
  entries.forEach(en => {
    if (en.isIntersecting) { countUp(en.target); countObs.unobserve(en.target); }
  });
}, { threshold: 0.5 });
document.querySelectorAll('[data-count]').forEach(el => countObs.observe(el));


// ── 4. PROGRESS BAR ANIMATION ────────────────────────────────────
const barObs = new IntersectionObserver(entries => {
  entries.forEach(en => {
    if (en.isIntersecting) {
      const w = en.target.getAttribute('data-width') || 0;
      setTimeout(() => { en.target.style.width = w + '%'; }, 120);
      barObs.unobserve(en.target);
    }
  });
}, { threshold: 0.3 });
document.querySelectorAll('.progress-bar-fill').forEach(el => barObs.observe(el));


// ── 5. SCROLL REVEAL ─────────────────────────────────────────────
const revealObs = new IntersectionObserver(entries => {
  entries.forEach((en, i) => {
    if (en.isIntersecting) {
      setTimeout(() => en.target.classList.add('visible'), i * 60);
      revealObs.unobserve(en.target);
    }
  });
}, { threshold: 0.08 });
document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));


// ── 6. STAGGERED CARD ENTRANCE ───────────────────────────────────
const cardObs = new IntersectionObserver(entries => {
  entries.forEach((en, i) => {
    if (en.isIntersecting) {
      setTimeout(() => en.target.classList.add('card-visible'), i * 75);
      cardObs.unobserve(en.target);
    }
  });
}, { threshold: 0.08 });
document.querySelectorAll('.course-card').forEach(el => cardObs.observe(el));


// ── 7. RIPPLE ON PRIMARY BUTTONS ─────────────────────────────────
document.querySelectorAll('.btn-primary-sf, .btn-enroll-big').forEach(btn => {
  btn.addEventListener('click', function(e) {
    const r    = document.createElement('span');
    r.className = 'ripple';
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    r.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
    btn.appendChild(r);
    setTimeout(() => r.remove(), 650);
  });
});


// ── 8. MAGNETIC BUTTONS ──────────────────────────────────────────
document.querySelectorAll('.btn-primary-sf, .btn-enroll-big, .sf-btn-ghost').forEach(btn => {
  btn.addEventListener('mousemove', function(e) {
    const rect = btn.getBoundingClientRect();
    const x = (e.clientX - rect.left - rect.width  / 2) * 0.18;
    const y = (e.clientY - rect.top  - rect.height / 2) * 0.18;
    btn.style.transform = `translate(${x}px, ${y}px)`;
  });
  btn.addEventListener('mouseleave', function() {
    btn.style.transform = '';
  });
});


// ── 9. MOUSE-TRACKING CARD BORDER GLOW ───────────────────────────
document.querySelectorAll('.course-card, .landing-course-card, .stat-card').forEach(card => {
  card.addEventListener('mousemove', function(e) {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width)  * 100;
    const y = ((e.clientY - rect.top)  / rect.height) * 100;
    card.style.setProperty('--mouse-x', x + '%');
    card.style.setProperty('--mouse-y', y + '%');
    card.style.background = `
      radial-gradient(circle at ${x}% ${y}%, rgba(124,58,237,0.07) 0%, transparent 60%),
      var(--card)
    `;
  });
  card.addEventListener('mouseleave', function() {
    card.style.background = '';
  });
});


// ── 10. SVG LINE DRAW ─────────────────────────────────────────────
document.querySelectorAll('.diagram-line').forEach((line, i) => {
  setTimeout(() => {
    line.style.transition = 'stroke-dashoffset 0.6s ease';
    line.style.strokeDashoffset = '0';
  }, 400 + i * 150);
});


// ── 11. GREETING ─────────────────────────────────────────────────
const greetingEl = document.getElementById('greeting');
if (greetingEl) {
  const hour = new Date().getHours();
  const name = greetingEl.textContent.split(',')[1]?.trim() || '';
  const prefix = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  greetingEl.textContent = `${prefix}, ${name}`;
}


// ── 12. AUTH PAGE COUNT-UP ON LOAD ───────────────────────────────
window.addEventListener('load', () => {
  document.querySelectorAll('.auth-stat-num[data-count]').forEach(el => {
    setTimeout(() => countUp(el), 600);
  });
});


// ── 13. HERO PARTICLES ───────────────────────────────────────────
const heroSection = document.querySelector('.landing-hero');
if (heroSection) {
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 3 + 1.5;
    const colors = ['rgba(124,58,237,0.6)','rgba(79,142,247,0.5)','rgba(167,139,250,0.4)'];
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random()*100}%;
      top:${60 + Math.random()*40}%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      animation-duration:${4 + Math.random()*6}s;
      animation-delay:${Math.random()*5}s;
      box-shadow: 0 0 ${size*2}px ${colors[0]};
    `;
    heroSection.appendChild(p);
  }
}


// ── 14. CTRL+K COMMAND PALETTE ───────────────────────────────────
function buildCommandPalette() {
  const overlay = document.createElement('div');
  overlay.id = 'cmd-overlay';
  overlay.style.cssText = `
    position:fixed; inset:0; background:rgba(0,0,0,0.7);
    backdrop-filter:blur(8px); z-index:9999;
    display:flex; align-items:flex-start; justify-content:center;
    padding-top:18vh; opacity:0; transition:opacity 0.2s ease;
    pointer-events:none;
  `;

  overlay.innerHTML = `
    <div id="cmd-box" style="
      background:#16161f; border:1px solid #252536;
      border-radius:16px; width:100%; max-width:520px;
      box-shadow:0 24px 80px rgba(0,0,0,0.6);
      transform:translateY(-12px); transition:transform 0.25s cubic-bezier(0.16,1,0.3,1);
      overflow:hidden;
    ">
      <div style="display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #1e1e2e;">
        <i class="bi bi-search" style="color:#55556a; font-size:0.95rem;"></i>
        <input id="cmd-input" placeholder="Search courses, pages..."
          style="flex:1; background:none; border:none; outline:none;
                 color:#f0f0f5; font-size:0.9rem; font-family:'Inter',sans-serif;"
          autocomplete="off">
        <kbd style="padding:2px 7px; background:#1e1e2e; border-radius:5px;
                    font-size:0.7rem; color:#55556a; font-family:'Inter',sans-serif;">ESC</kbd>
      </div>
      <div id="cmd-results" style="padding:8px; max-height:320px; overflow-y:auto;"></div>
    </div>
  `;

  document.body.appendChild(overlay);

  const links = [
    { label: 'Dashboard',       icon: 'bi-speedometer2', url: '/dashboard' },
    { label: 'Browse Courses',  icon: 'bi-grid',         url: '/courses' },
    { label: 'My Learning',     icon: 'bi-journal-check',url: '/my-learning' },
    { label: 'Admin Panel',     icon: 'bi-shield-fill',  url: '/admin/courses' },
    { label: 'Logout',          icon: 'bi-box-arrow-right', url: '/logout' },
  ];

  function renderResults(query) {
    const res = document.getElementById('cmd-results');
    const filtered = query
      ? links.filter(l => l.label.toLowerCase().includes(query.toLowerCase()))
      : links;
    if (!filtered.length) {
      res.innerHTML = `<div style="padding:20px;text-align:center;color:#55556a;font-size:0.83rem;">No results</div>`;
      return;
    }
    res.innerHTML = filtered.map((l, i) => `
      <a href="${l.url}" style="
        display:flex; align-items:center; gap:10px; padding:10px 12px;
        border-radius:8px; text-decoration:none; color:#8888a0;
        font-size:0.85rem; transition:all 0.15s ease;
        ${i === 0 ? 'background:rgba(124,58,237,0.08);color:#f0f0f5;' : ''}
      "
      onmouseover="this.style.background='rgba(255,255,255,0.05)';this.style.color='#f0f0f5';"
      onmouseout="this.style.background='${i===0?'rgba(124,58,237,0.08)':''}';this.style.color='${i===0?'#f0f0f5':'#8888a0'}'"
      >
        <i class="bi ${l.icon}" style="font-size:0.9rem;width:18px;text-align:center;"></i>
        ${l.label}
      </a>
    `).join('');
  }

  function open() {
    overlay.style.pointerEvents = 'all';
    overlay.style.opacity = '1';
    document.getElementById('cmd-box').style.transform = 'translateY(0)';
    document.getElementById('cmd-input').value = '';
    renderResults('');
    setTimeout(() => document.getElementById('cmd-input').focus(), 50);
  }
  function close() {
    overlay.style.opacity = '0';
    overlay.style.pointerEvents = 'none';
    document.getElementById('cmd-box').style.transform = 'translateY(-12px)';
  }

  document.getElementById('cmd-input').addEventListener('input', e => renderResults(e.target.value));
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); open(); }
    if (e.key === 'Escape') close();
  });
}

if (document.querySelector('.sf-nav')) buildCommandPalette();
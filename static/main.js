// ================================================================
// SkillForge — main.js
// All animations: count-up, progress bars, staggered cards,
// SVG line drawing, greeting, ripple buttons
// ================================================================


// ── 1. Greeting by time of day ──────────────────────────────────
const greetingEl = document.getElementById('greeting');
if (greetingEl) {
    const hour = new Date().getHours();
    const name = greetingEl.textContent.split(',')[1]?.trim() || '';
    let prefix = 'Good evening';
    if (hour < 12) prefix = 'Good morning';
    else if (hour < 17) prefix = 'Good afternoon';
    greetingEl.textContent = `${prefix}, ${name}`;
}


// ── 2. Count-up animation ───────────────────────────────────────
// [EXPLANATION] IntersectionObserver: Browser API hai — element screen
// pe visible ho tab callback fire karta hai, pehle nahi
function countUp(el) {
    const target   = parseInt(el.getAttribute('data-count')) || 0;
    const duration = 1200;
    const start    = performance.now();

    function update(now) {
        const elapsed  = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out curve — fast start, slow end
        const eased    = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target).toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
        else el.textContent = target.toLocaleString();
    }

    requestAnimationFrame(update);
}

const countObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            countUp(entry.target);
            countObserver.unobserve(entry.target); // Run only once
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('[data-count]').forEach(el => countObserver.observe(el));


// ── 3. Progress bar animation ───────────────────────────────────
const barObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const fill      = entry.target;
            const targetW   = fill.getAttribute('data-width') || 0;
            // Small delay then set width — CSS transition handles animation
            setTimeout(() => { fill.style.width = targetW + '%'; }, 100);
            barObserver.unobserve(fill);
        }
    });
}, { threshold: 0.3 });

document.querySelectorAll('.progress-bar-fill').forEach(el => barObserver.observe(el));


// ── 4. Staggered card entrance animation ────────────────────────
// [EXPLANATION] stagger: Cards ek saath nahi, ek ek karke thodi
// delay ke saath appear hoti hain — ye effect professional lagta hai
const cards = document.querySelectorAll('.course-card');
const cardObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
            setTimeout(() => {
                entry.target.classList.add('card-visible');
            }, i * 80); // 80ms gap between each card
            cardObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

cards.forEach(card => cardObserver.observe(card));


// ── 5. SVG diagram line drawing animation ───────────────────────
// [EXPLANATION] stroke-dashoffset: SVG lines ko "undrawn" state mein
// rakhte hain phir animate karke draw karte hain — Claude wali animation!
document.querySelectorAll('.diagram-line').forEach((line, i) => {
    setTimeout(() => {
        line.style.transition = 'stroke-dashoffset 0.6s ease';
        line.style.strokeDashoffset = '0';
    }, 400 + i * 150); // Each line draws after previous
});


// ── 6. Ripple effect on primary buttons ─────────────────────────
document.querySelectorAll('.btn-primary-sf').forEach(btn => {
    btn.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');

        const rect   = btn.getBoundingClientRect();
        const size   = Math.max(rect.width, rect.height);
        ripple.style.width  = ripple.style.height = size + 'px';
        ripple.style.left   = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top    = (e.clientY - rect.top  - size / 2) + 'px';

        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
    });
});


// ── 7. Auth stat count-up on load ───────────────────────────────
// Auth page pe observer kaam nahi karta (already visible) — seedha run
window.addEventListener('load', () => {
    document.querySelectorAll('.auth-stat-num[data-count]').forEach(el => {
        setTimeout(() => countUp(el), 800);
    });
});
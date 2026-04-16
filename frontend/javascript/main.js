const canvas = document.getElementById("liquid-canvas");
const ctx = canvas?.getContext("2d");

function resize() {
  if (!canvas) return;
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

resize();
window.addEventListener("resize", resize);

const drops = Array.from({ length: 18 }, () => ({
  x: Math.random(),
  y: Math.random(),
  r: Math.random() * 120 + 40,
  dx: (Math.random() - 0.5) * 0.0009,
  dy: (Math.random() - 0.5) * 0.0009,
}));

function draw() {
  if (!ctx || !canvas) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (const b of drops) {
    b.x += b.dx;
    b.y += b.dy;

    if (b.x < -0.2 || b.x > 1.2) b.dx *= -1;
    if (b.y < -0.2 || b.y > 1.2) b.dy *= -1;

    const x = b.x * canvas.width;
    const y = b.y * canvas.height;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, b.r);
    grad.addColorStop(0, "rgba(149, 214, 255, 0.22)");
    grad.addColorStop(1, "rgba(149, 214, 255, 0)");

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, b.r, 0, Math.PI * 2);
    ctx.fill();
  }

  requestAnimationFrame(draw);
}

draw();

// Modal functions for projects
function openProjectsModal() {
  document.getElementById("projectsModal").style.display = "block";
}

function closeProjectsModal() {
  document.getElementById("projectsModal").style.display = "none";
}

// Close modal when clicking outside of it
window.onclick = function(event) {
  const modal = document.getElementById("projectsModal");
  if (event.target == modal) {
    modal.style.display = "none";
  }
}

const tiltCards = document.querySelectorAll(".tilt-card");
for (const card of tiltCards) {
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    const rx = (-y * 8).toFixed(2);
    const ry = (x * 8).toFixed(2);
    card.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg) translateZ(8px)`;
  });

  card.addEventListener("mouseleave", () => {
    card.style.transform = "rotateX(0deg) rotateY(0deg) translateZ(0px)";
  });
}

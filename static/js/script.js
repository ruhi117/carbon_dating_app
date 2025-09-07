
window.addEventListener('load', () => {
  const splash = document.getElementById('splash');
  if (splash) {
    splash.style.display = 'none';
  }
});


const btn = document.getElementById('menu-btn');
const menu = document.getElementById('mobile-menu');

if (btn && menu) {
  btn.addEventListener('click', () => {
    menu.classList.toggle('hidden');
  });
}


const faders = document.querySelectorAll('.fade-in-up');

const appearOptions = {
  threshold: 0.3,
  rootMargin: "0px 0px -50px 0px"
};

const appearOnScroll = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('appear');
      observer.unobserve(entry.target);
    }
  });
}, appearOptions);

faders.forEach(fader => appearOnScroll.observe(fader));


const slides = document.querySelectorAll('.slide');

const slideObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('opacity-100');
      entry.target.classList.remove('opacity-0');
    }
  });
}, { threshold: 0.3 });

slides.forEach(slide => slideObserver.observe(slide));






window.addEventListener("DOMContentLoaded", () => {
  gsap.registerPlugin(ScrollTrigger);

  const slidesContainer = document.querySelector(".slides-container");

  gsap.utils.toArray(".slide").forEach((slide, i) => {
    gsap.from(slide, {
      opacity: 0,
      y: 50,
      duration: 1,
      delay: i * 0.2,
      scrollTrigger: {
        trigger: slide,
        scroller: slidesContainer, 
        start: "top 80%",
        toggleActions: "play none none none"
      }
    });

    const h2 = slide.querySelector("h2");
    const p = slide.querySelector("p");
    const a = slide.querySelector("a");

    if (h2) {
      gsap.from(h2, {
        opacity: 0,
        y: 50,
        duration: 1,
        scrollTrigger: {
          trigger: slide,
          scroller: slidesContainer,
          start: "top 80%"
        }
      });
    }

    if (p) {
      gsap.from(p, {
        opacity: 0,
        x: -50,
        duration: 1,
        delay: 0.3,
        scrollTrigger: {
          trigger: slide,
          scroller: slidesContainer,
          start: "top 75%"
        }
      });
    }

    if (a) {
      gsap.from(a, {
        opacity: 0,
        scale: 0.8,
        duration: 1,
        delay: 0.6,
        scrollTrigger: {
          trigger: slide,
          scroller: slidesContainer,
          start: "top 70%"
        }
      });
    }
  });
});


window.addEventListener("DOMContentLoaded", () => {
  gsap.registerPlugin(ScrollTrigger);

  const overlay = document.getElementById("hero-overlay");
  const overlayText = document.getElementById("overlay-text");
  const heroText = document.getElementById("hero-text");
  const heroVideo = document.getElementById("hero-video");


  gsap.timeline()
    .to(overlayText, { opacity: 0, duration: 3 })
    .to(overlay, { opacity: 0, duration: 1, onComplete: () => overlay.style.display = 'none' })
    .to(heroText, { opacity: 1, scale: 1.05, duration: 2, ease: "power2.out" })
    .to(heroText, { y: -20, repeat: -1, yoyo: true, duration: 2, ease: "power1.inOut" });
});

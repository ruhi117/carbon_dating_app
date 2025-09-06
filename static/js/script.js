// ================================
// Splash Screen Fade Out
// ================================
window.addEventListener('DOMContentLoaded', () => {
    const splash = document.getElementById('splash');
    const slidesContainer = document.querySelector('.slides-container');

    // Hide splash after click or timeout
    const hideSplash = () => {
        splash.classList.add('hide');
        // Enable scrolling after splash
        slidesContainer.style.overflowY = 'scroll';
    };

    // Optional: hide splash after 3 seconds automatically
    setTimeout(hideSplash, 3000);

    // Hide splash on click anywhere
    splash.addEventListener('click', hideSplash);
});

// ================================
// Smooth Scroll for CTA Buttons
// ================================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if(target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// ================================
// Fade-in Animations on Scroll
// ================================
const faders = document.querySelectorAll('.fade-in-up');

const appearOptions = {
    threshold: 0.3,
    rootMargin: "0px 0px -50px 0px"
};

const appearOnScroll = new IntersectionObserver((entries, appearOnScroll) => {
    entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('appear');
        appearOnScroll.unobserve(entry.target);
    });
}, appearOptions);

faders.forEach(fader => {
    appearOnScroll.observe(fader);
});

window.addEventListener('load', () => {
    setTimeout(() => {
        document.getElementById('splash').style.display = 'none';
    }, 2500); // hide after 2.5s
});

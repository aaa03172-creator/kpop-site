document.addEventListener('DOMContentLoaded', () => {
    
    /* ==========================================
       1. Header Scroll Effect
       ========================================== */
    const header = document.getElementById('header');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    /* ==========================================
       2. Mobile Menu Toggle
       ========================================== */
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            menuToggle.classList.toggle('active');
        });
    }

    // Close mobile menu when clicking a link
    const navItems = document.querySelectorAll('.nav-links a');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                menuToggle.classList.remove('active');
            }
        });
    });

    /* ==========================================
       3. Contact Form Submission (UI Demo)
       ========================================== */
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault(); // Prevent actual submission for demo
            
            // Get form values
            const nameInput = document.getElementById('name');
            const name = nameInput.value;
            
            // Simple validation and alert
            if(name.trim() !== "") {
                alert(`감사합니다, ${name}님!\n문의가 성공적으로 접수되었습니다. 곧 답변 드리겠습니다.\n(이는 프론트엔드 UI 데모입니다)`);
                
                // Reset form
                contactForm.reset();
            }
        });
    }

    /* ==========================================
       4. Scroll Fade-in Animation
       ========================================== */
    // Apply animation classes to elements
    const fadeElements = document.querySelectorAll('.product-text, .product-specs, .feature-card, .story-container, .contact-container');
    
    // Initial state setup
    fadeElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.8s ease-out, transform 0.8s ease-out';
    });

    // Intersection Observer callback
    const observerCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Add staggered delay based on order for feature cards
                if(entry.target.classList.contains('feature-card')) {
                    // Find index of the card among siblings
                    const parent = entry.target.parentElement;
                    const children = Array.from(parent.children);
                    const index = children.indexOf(entry.target);
                    entry.target.style.transitionDelay = `${index * 0.15}s`;
                }
                
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                
                // Stop observing once animated
                observer.unobserve(entry.target);
            }
        });
    };

    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15 // Trigger when 15% of element is visible
    };

    const observer = new IntersectionObserver(observerCallback, observerOptions);

    fadeElements.forEach(el => {
        observer.observe(el);
    });
});

/*

Tooplate 2143 Inner Peace

https://www.tooplate.com/view/2143-inner-peace

Free HTML CSS Template

*/

// JavaScript Document

// Mobile menu toggle


        function toggleMenu() {
            const menuToggle = document.querySelector('.menu-toggle');
            const navLinks = document.querySelector('.nav-links');
            if (menuToggle && navLinks) {
                menuToggle.classList.toggle('active');
                navLinks.classList.toggle('active');
            }
        }

        // Close mobile menu when clicking a link
        document.addEventListener('DOMContentLoaded', function() {
            const navLinks = document.querySelectorAll('.nav-links a');
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    const menuToggle = document.querySelector('.menu-toggle');
                    const navLinksContainer = document.querySelector('.nav-links');
                    if (menuToggle && navLinksContainer) {
                        menuToggle.classList.remove('active');
                        navLinksContainer.classList.remove('active');
                    }
                });
            });

            // Active menu highlighting
            const sections = document.querySelectorAll('section');
            const menuLinks = document.querySelectorAll('.nav-link');

            if (sections.length && menuLinks.length) {
                window.addEventListener('scroll', () => {
                    let current = '';
                    sections.forEach(section => {
                        const sectionTop = section.offsetTop;
                        const sectionHeight = section.clientHeight;
                        if (window.scrollY >= (sectionTop - 200)) {
                            current = section.getAttribute('id');
                        }
                    });

                    menuLinks.forEach(link => {
                        link.classList.remove('active');
                        const href = link.getAttribute('href');
                        if (href && href.slice(1) === current) {
                            link.classList.add('active');
                        }
                    });
                });
            }

            // Smooth scrolling for anchor links
            const anchorLinks = document.querySelectorAll('a[href^="#"]');
            anchorLinks.forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    const href = this.getAttribute('href');
                    if (href && href !== '#') {
                        e.preventDefault();
                        const target = document.querySelector(href);
                        if (target) {
                            target.scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                            });
                        }
                    }
                });
            });

            // Header scroll effect
            const header = document.querySelector('header');
            if (header) {
                window.addEventListener('scroll', () => {
                    if (window.scrollY > 100) {
                        header.style.background = 'rgba(255, 255, 255, 0.98)';
                        header.style.boxShadow = '0 2px 30px rgba(0, 0, 0, 0.1)';
                    } else {
                        header.style.background = 'rgba(255, 255, 255, 0.95)';
                        header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.05)';
                    }
                });
            }

            // Tab functionality
            window.showTab = function(tabName) {
                const tabs = document.querySelectorAll('.tab-content');
                const buttons = document.querySelectorAll('.tab-btn');
                
                tabs.forEach(tab => {
                    tab.classList.remove('active');
                });
                
                buttons.forEach(btn => {
                    btn.classList.remove('active');
                });
                
                const targetTab = document.getElementById(tabName);
                if (targetTab) {
                    targetTab.classList.add('active');
                }
                
                // Find and activate the clicked button
                buttons.forEach(btn => {
                    if (btn.textContent.toLowerCase().includes(tabName.toLowerCase())) {
                        btn.classList.add('active');
                    }
                });
            };

            // Form submission handler
            const contactForm = document.querySelector('.contact-form form');
            if (contactForm) {
                contactForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    alert('Thank you for reaching out! We will get back to you soon.');
                    e.target.reset();
                });
            }
        });

        

/*
document.addEventListener('DOMContentLoaded', function() {
    const esp32IP = "http://192.168.43.22:80"; // Cambia por la IP real del ESP32

    // Función para enviar comando al ESP32
    function sendCommand(command) {
        fetch(`${esp32IP}/buzzer?state=${command}`)
            .then(response => console.log(`Comando enviado: ${command}`))
            .catch(error => console.error("Error:", error));
    }
        
        
       
    // Botón 1
    const btn1 = document.getElementById('btn1');
    if (btn1) {
        btn1.addEventListener('click', () => sendCommand('on1'));
    }

    // Botón 2
    const btn2 = document.getElementById('btn2');
    if (btn2) {
        btn2.addEventListener('click', () => sendCommand('on2'));
    }

    // Botón 3
    const btn3 = document.getElementById('btn3');
    if (btn3) {
        btn3.addEventListener('click', () => sendCommand('on3'));
    }

    

    
    document.getElementById('btn1').addEventListener('click', () => sendCommand('on1'));
    document.getElementById('btn2').addEventListener('click', () => sendCommand('on2'));
    document.getElementById('btn3').addEventListener('click', () => sendCommand('on3'));

});
 */

/* 
Tooplate 2143 Inner Peace
https://www.tooplate.com/view/2143-inner-peace
Free HTML CSS 
*/
// JavaScript Document

// (Se mantienen las funciones de UI del template...)
// ...

document.addEventListener('DOMContentLoaded', function() {
  const esp32IP = "http://192.168.1.173:80"; // Cambia por tu IP real

  function sendCommand(command) {
    fetch(`${esp32IP}/buzzer?state=${command}`)
      .then(() => console.log(`Comando enviado: ${command}`))
      .catch(error => console.error("Error:", error));
  }

  // Botones de buzzer
  document.getElementById('btn1')?.addEventListener('click', () => sendCommand('on1'));
  document.getElementById('btn2')?.addEventListener('click', () => sendCommand('on2'));
  document.getElementById('btn3')?.addEventListener('click', () => sendCommand('on3'));
  document.getElementById('stop')?.addEventListener('click', () => sendCommand('STOP'));

  // *** Eliminado: setInterval para /alert y manejo de alert-container ***

  // Actualización de HR/SpO2 desde el ESP32
  function updateVitals() {
    fetch(`${esp32IP}/vitals`)
      .then(r => r.json())
      .then(v => {
        const hrEl = document.getElementById('hr');
        const hrCatEl = document.getElementById('hr_cat');
        const spo2El = document.getElementById('spo2');
        const spo2CatEl = document.getElementById('spo2_cat');
        const tempEl = document.getElementById('temp');         // <-- nuevo
        const tempCatEl = document.getElementById('temp_cat');  // <-- nuevo


        if (hrEl)      hrEl.textContent      = (v.hr   === null) ? '--' : Number(v.hr).toFixed(1);
        if (hrCatEl)   hrCatEl.textContent   = v.hr_cat   || 'sin dato';
        if (spo2El)    spo2El.textContent    = (v.spo2 === null) ? '--' : Number(v.spo2).toFixed(1);
        if (spo2CatEl) spo2CatEl.textContent = v.spo2_cat || 'sin dato';
        if (tempEl)    tempEl.textContent    = (v.temp === null) ? '--' : Number(v.temp).toFixed(2);
        if (tempCatEl) tempCatEl.textContent = v.temp_cat || 'sin dato';
      })
      .catch(err => console.error('Error al consultar /vitals:', err));
  }
  setInterval(updateVitals, 1000);
});



     
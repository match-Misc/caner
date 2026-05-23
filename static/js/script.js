document.addEventListener('DOMContentLoaded', function() {
    // Dark mode functionality
    const darkModeToggle = document.getElementById('darkModeToggle');
    const html = document.documentElement;
    const darkModeIcon = darkModeToggle ? darkModeToggle.querySelector('i') : null;

    // Check if dark mode is already enabled in localStorage
    const isDarkMode = localStorage.getItem('darkMode') === 'enabled';

    // Set initial dark mode state (icon only, theme is set by inline script)
    if (isDarkMode && darkModeIcon) {
        darkModeIcon.classList.remove('fa-moon');
        darkModeIcon.classList.add('fa-sun');
    }

    // Add click event listener to the dark mode toggle button
    if (darkModeToggle && darkModeIcon) {
        darkModeToggle.addEventListener('click', function() {
            if (html.getAttribute('data-theme') === 'dark') {
                // Switch to light mode
                html.removeAttribute('data-theme');
                localStorage.setItem('darkMode', 'disabled');
                darkModeIcon.classList.remove('fa-sun');
                darkModeIcon.classList.add('fa-moon');
            } else {
                // Switch to dark mode
                html.setAttribute('data-theme', 'dark');
                localStorage.setItem('darkMode', 'enabled');
                darkModeIcon.classList.remove('fa-moon');
                darkModeIcon.classList.add('fa-sun');
            }
        });
    }

    const languageOptions = document.querySelectorAll('.language-option[data-lang]');
    languageOptions.forEach(option => {
        option.addEventListener('click', function() {
            const targetLang = option.dataset.lang;
            if (!targetLang || option.classList.contains('active')) {
                return;
            }

            const url = new URL(window.location);
            url.searchParams.set('lang', targetLang);
            window.location.href = url.toString();
        });
    });

    const mobilePriceSelectors = document.querySelectorAll('.mobile-price-selector');
    mobilePriceSelectors.forEach(selector => {
        const buttons = selector.querySelectorAll('.mobile-price-selector-button');
        const mobileMenu = selector.closest('.mobile-meal-cards');

        function selectPriceType(priceType) {
            buttons.forEach(button => {
                const isActive = button.dataset.priceType === priceType;
                button.classList.toggle('active', isActive);
                button.setAttribute('aria-pressed', isActive.toString());
            });

            if (!mobileMenu) {
                return;
            }

            mobileMenu.querySelectorAll('.mobile-user-info-row[data-price-type]').forEach(row => {
                row.classList.toggle('d-none', row.dataset.priceType !== priceType);
            });
        }

        buttons.forEach(button => {
            button.addEventListener('click', function() {
                selectPriceType(button.dataset.priceType || 'student');
            });
        });

        selectPriceType('student');
    });
    
    // Initialize meal voting system
    initMealVoting();
    
    // Meal voting functionality
    function initMealVoting() {
        // Find all vote controls in the document
        const voteControls = document.querySelectorAll('.vote-controls');
        
        // For each vote control section
        voteControls.forEach(controls => {
            const mealId = controls.dataset.mealId;
            const upvoteBtn = controls.querySelector('.upvote-btn');
            const downvoteBtn = controls.querySelector('.downvote-btn');
            const upvoteCount = controls.querySelector('.upvote-count');
            const downvoteCount = controls.querySelector('.downvote-count');
            
            // Skip if any element is missing
            if (!mealId || !upvoteBtn || !downvoteBtn || !upvoteCount || !downvoteCount) {
                console.error('Missing elements in vote controls');
                return;
            }
            
            // Load initial vote counts from the server
            loadVoteCounts(mealId, upvoteCount, downvoteCount, upvoteBtn, downvoteBtn);
            
            // Add event listeners for vote buttons
            upvoteBtn.addEventListener('click', function() {
                submitVote(mealId, 'up', upvoteCount, downvoteCount, upvoteBtn, downvoteBtn);
            });
            
            downvoteBtn.addEventListener('click', function() {
                submitVote(mealId, 'down', upvoteCount, downvoteCount, upvoteBtn, downvoteBtn);
            });
        });
    }
    
    // Load vote counts from the server
    function loadVoteCounts(mealId, upvoteCount, downvoteCount, upvoteBtn, downvoteBtn) {
        fetch(`/api/votes/${mealId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Update vote counts
                upvoteCount.textContent = data.votes.up;
                downvoteCount.textContent = data.votes.down;
                
                // If the user has already voted, highlight the button
                if (data.has_voted) {
                    // Check user's stored votes in local storage
                    const storedVote = localStorage.getItem(`meal_vote_${mealId}`);
                    if (storedVote === 'up') {
                        upvoteBtn.classList.add('active');
                    } else if (storedVote === 'down') {
                        downvoteBtn.classList.add('active');
                    }
                }
            })
            .catch(error => {
                console.error('Error loading vote counts:', error);
            });
    }
    
    // Submit a vote to the server
    function submitVote(mealId, voteType, upvoteCount, downvoteCount, upvoteBtn, downvoteBtn) {
        // Create request payload
        const payload = {
            meal_id: mealId,
            vote_type: voteType
        };
        
        // Send the vote to the server
        fetch('/api/vote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update vote counts
            upvoteCount.textContent = data.votes.up;
            downvoteCount.textContent = data.votes.down;
            
            // Update active state of vote buttons
            upvoteBtn.classList.toggle('active', voteType === 'up');
            downvoteBtn.classList.toggle('active', voteType === 'down');
            
            // Store the vote in local storage to remember which button was clicked
            localStorage.setItem(`meal_vote_${mealId}`, voteType);
        })
        .catch(error => {
            console.error('Error submitting vote:', error);
        });
    }
    

    // Expert Mode Toggle
    const expertModeToggleIcon = document.getElementById('expertModeToggleIcon');
    const expertModeCols = document.querySelectorAll('.expert-mode-col');
    
    // Check URL parameter for expert mode - URL is the source of truth
    const urlParams = new URLSearchParams(window.location.search);
    const expertModeFromUrl = urlParams.get('expert') === 'true';

    // Set expertModeEnabled based on URL parameter (backend controls the state)
    // When URL has ?expert=true, enable expert mode
    // Otherwise, expert mode is OFF by default
    let expertModeEnabled = expertModeFromUrl;
    
    // Sync localStorage with the URL state to maintain consistency
    localStorage.setItem('expertModeEnabled', expertModeEnabled.toString());

    // Helper functions for color interpolation
    function hexToRgb(hex) {
        let r = 0, g = 0, b = 0;
        if (hex.length === 4) { // #RGB
            r = parseInt(hex[1] + hex[1], 16);
            g = parseInt(hex[2] + hex[2], 16);
            b = parseInt(hex[3] + hex[3], 16);
        } else if (hex.length === 7) { // #RRGGBB
            r = parseInt(hex.substring(1, 3), 16);
            g = parseInt(hex.substring(3, 5), 16);
            b = parseInt(hex.substring(5, 7), 16);
        }
        return { r, g, b };
    }

    function rgbToHex(r, g, b) {
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).padStart(6, '0');
    }

    function interpolateColor(colorStartHex, colorEndHex, factor) {
        // Clamp factor to [0, 1]
        const t = Math.max(0, Math.min(1, factor));

        const rgbStart = hexToRgb(colorStartHex);
        const rgbEnd = hexToRgb(colorEndHex);

        const r = Math.round(rgbStart.r + t * (rgbEnd.r - rgbStart.r));
        const g = Math.round(rgbStart.g + t * (rgbEnd.g - rgbStart.g));
        const b = Math.round(rgbStart.b + t * (rgbEnd.b - rgbStart.b));

        return rgbToHex(r, g, b);
    }

    function applyExpertModeStyles() {
        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        let colorNegative, colorPositive, colorCenter;

        if (isDarkMode) {
            colorNegative = '#ff5555'; // Dark mode Downvote Red
            colorCenter = '#FFB86C';   // Dark mode Center Yellow/Orange
            colorPositive = '#50fa7b'; // Dark mode Upvote Green
        } else {
            colorNegative = '#dc3545'; // Light mode Downvote Red
            colorCenter = '#ffcc00';   // Light mode Center Yellow
            colorPositive = '#28a745'; // Light mode Upvote Green
        }

        expertModeCols.forEach(col => {
            if (col.tagName === 'TH' || col.tagName === 'TD') {
                col.style.display = expertModeEnabled ? 'table-cell' : 'none';
            } else { // For mobile view elements (divs behaving as rows/items)
                col.style.display = expertModeEnabled ? 'flex' : 'none';
            }
        });
        if (expertModeToggleIcon) {
            expertModeToggleIcon.style.opacity = '1';
            expertModeToggleIcon.classList.toggle('active', expertModeEnabled);
            expertModeToggleIcon.setAttribute('aria-pressed', expertModeEnabled.toString());
        }

        const canerElements = document.querySelectorAll('.caner-symbols');
        const rkrElements = document.querySelectorAll('strong.rkr-value');
        const mpsElements = document.querySelectorAll('strong.mps-value');

        if (expertModeEnabled) {
            canerElements.forEach(el => {
                const canerValueText = el.dataset.canerValue;
                if (canerValueText === undefined) return;

                const canerValue = parseFloat(canerValueText);
                if (!isNaN(canerValue)) {
                    const scaleMaxCaner = 600; // Max value for pure positive color
                    let finalColor;
                    const visualMidPointCaner = scaleMaxCaner / 2; // Midpoint for color transition

                    if (canerValue <= 0) {
                        finalColor = colorNegative;
                    } else if (canerValue >= scaleMaxCaner) {
                        finalColor = colorPositive;
                    } else if (canerValue <= visualMidPointCaner) {
                        // Interpolate from colorNegative (at 0) to colorCenter (at visualMidPointCaner)
                        const factor = canerValue / visualMidPointCaner;
                        finalColor = interpolateColor(colorNegative, colorCenter, factor);
                    } else {
                        // Interpolate from colorCenter (at visualMidPointCaner) to colorPositive (at scaleMaxCaner)
                        const factor = (canerValue - visualMidPointCaner) / (scaleMaxCaner - visualMidPointCaner);
                        finalColor = interpolateColor(colorCenter, colorPositive, factor);
                    }
                    el.style.color = finalColor;
                }
            });

            // Reorder spans for expert mode: caner-value first for desktop, caner-symbol first for mobile
            canerElements.forEach(el => {
                const canerValueSpan = el.querySelector('.caner-value');
                const canerSymbolSpan = el.querySelector('.caner-symbol');
                if (canerValueSpan && canerSymbolSpan) {
                    if (el.parentElement.classList.contains('mobile-layout')) {
                        // For mobile expert, caner-symbol first, then caner-value
                        el.insertBefore(canerSymbolSpan, canerValueSpan);
                    } else {
                        // For desktop expert, caner-value first
                        el.insertBefore(canerValueSpan, canerSymbolSpan);
                    }
                }
            });

            rkrElements.forEach(el => {
                const textValue = el.textContent.replace(',', '.').replace(/[^\d.-]/g, '');
                const rkrValue = parseFloat(textValue);

                if (!isNaN(rkrValue)) {
                    const scaleMaxRkr = 20; // Max value for pure positive color
                    let finalColor;
                    const visualMidPointRkr = scaleMaxRkr / 2; // Midpoint for color transition

                    if (rkrValue <= 0) {
                        finalColor = colorNegative;
                    } else if (rkrValue >= scaleMaxRkr) {
                        finalColor = colorPositive;
                    } else if (rkrValue <= visualMidPointRkr) {
                        // Interpolate from colorNegative (at 0) to colorCenter (at visualMidPointRkr)
                        const factor = rkrValue / visualMidPointRkr;
                        finalColor = interpolateColor(colorNegative, colorCenter, factor);
                    } else {
                        // Interpolate from colorCenter (at visualMidPointRkr) to colorPositive (at scaleMaxRkr)
                        const factor = (rkrValue - visualMidPointRkr) / (scaleMaxRkr - visualMidPointRkr);
                        finalColor = interpolateColor(colorCenter, colorPositive, factor);
                    }
                    el.style.color = finalColor;
                }
            });

            mpsElements.forEach(el => {
                const textValue = el.textContent.replace(',', '.').replace(/[^\d.-]/g, '');
                const mpsValue = parseFloat(textValue);

                if (!isNaN(mpsValue)) {
                    const scaleMaxMps = 100; // Max value for pure positive color (0-100 scale)
                    let finalColor;
                    const visualMidPointMps = scaleMaxMps / 2; // Midpoint for color transition

                    if (mpsValue <= 0) {
                        finalColor = colorNegative;
                    } else if (mpsValue >= scaleMaxMps) {
                        finalColor = colorPositive;
                    } else if (mpsValue <= visualMidPointMps) {
                        // Interpolate from colorNegative (at 0) to colorCenter (at visualMidPointMps)
                        const factor = mpsValue / visualMidPointMps;
                        finalColor = interpolateColor(colorNegative, colorCenter, factor);
                    } else {
                        // Interpolate from colorCenter (at visualMidPointMps) to colorPositive (at scaleMaxMps)
                        const factor = (mpsValue - visualMidPointMps) / (scaleMaxMps - visualMidPointMps);
                        finalColor = interpolateColor(colorCenter, colorPositive, factor);
                    }
                    el.style.color = finalColor;
                }
            });

        } else { // Expert mode disabled
            canerElements.forEach(el => {
                el.style.color = ''; // Reset color
            });
            rkrElements.forEach(el => {
                el.style.color = ''; // Reset color
            });
            mpsElements.forEach(el => {
                el.style.color = ''; // Reset color
            });

            // Reorder spans for non-expert mode: caner-symbol first, then caner-value
            canerElements.forEach(el => {
                const canerValueSpan = el.querySelector('.caner-value');
                const canerSymbolSpan = el.querySelector('.caner-symbol');
                if (canerValueSpan && canerSymbolSpan) {
                    el.insertBefore(canerSymbolSpan, canerValueSpan);
                }
            });
        }
    }

    if (expertModeToggleIcon) {
        applyExpertModeStyles(); // Apply initial state on load

        expertModeToggleIcon.addEventListener('click', function() {
            expertModeEnabled = !expertModeEnabled; // Toggle the state
            localStorage.setItem('expertModeEnabled', expertModeEnabled.toString());
            applyExpertModeStyles();

            // Reload the page with the expert parameter to apply the change
            const url = new URL(window.location);
            if (expertModeEnabled) {
                url.searchParams.set('expert', 'true');
            } else {
                url.searchParams.delete('expert');
            }
            window.location.href = url.toString();
        });
    }

});

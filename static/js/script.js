document.addEventListener('DOMContentLoaded', function() {
    // Initialize meal recommendation functionality - Removed
    // initMealRecommendation(); 
    
    // Dark mode functionality
    const darkModeToggle = document.getElementById('darkModeToggle');
    const html = document.documentElement;
    const darkModeIcon = darkModeToggle.querySelector('i');

    // Check if dark mode is already enabled in localStorage
    const isDarkMode = localStorage.getItem('darkMode') === 'enabled';

    // Set initial dark mode state (icon only, theme is set by inline script)
    if (isDarkMode) {
        // html.setAttribute('data-theme', 'dark'); // Redundant: This is now handled by the inline script in base.html
        darkModeIcon.classList.remove('fa-moon');
        darkModeIcon.classList.add('fa-sun');
    }

    // Add click event listener to the dark mode toggle button
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

    // Dashboard mode functionality
    const dashboardModeToggle = document.getElementById('dashboardModeToggle');
    
    // Check current URL parameter to determine actual dashboard state
    const url = new URL(window.location);
    const isDashboardModeActiveInURL = url.searchParams.get('dashboard') === 'true';
    
    // Synchronize localStorage with the actual URL state
    localStorage.setItem('dashboardMode', isDashboardModeActiveInURL ? 'enabled' : 'disabled');
    let dashboardModeEnabled = isDashboardModeActiveInURL;

    function applyDashboardModeStyles() {
        if (dashboardModeToggle) {
            dashboardModeToggle.style.opacity = dashboardModeEnabled ? '1' : '0.5';
        }
    }

    if (dashboardModeToggle) {
        applyDashboardModeStyles(); // Apply initial state on load

        dashboardModeToggle.addEventListener('click', function() {
            dashboardModeEnabled = !dashboardModeEnabled; // Toggle the state
            localStorage.setItem('dashboardMode', dashboardModeEnabled ? 'enabled' : 'disabled');
            applyDashboardModeStyles();

            // Reload the page with the dashboard parameter to apply the change
            const url = new URL(window.location);
            if (dashboardModeEnabled) {
                url.searchParams.set('dashboard', 'true');
            } else {
                url.searchParams.delete('dashboard');
            }
            window.location.href = url.toString();
        });
    }
    
    // Make table rows clickable to show/hide nutritional information on mobile
    const mealRows = document.querySelectorAll('.meal-table tbody tr');
    
    mealRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Ignore clicks on vote buttons
            if (e.target.closest('.vote-btn') || e.target.closest('.vote-controls')) {
                return;
            }
            
            // Check if we're on mobile
            if (window.innerWidth <= 768) {
                const nutritionalInfo = this.querySelector('.nutritional-info');
                if (nutritionalInfo) {
                    // Toggle the display of nutritional info
                    if (nutritionalInfo.style.display === 'block') {
                        nutritionalInfo.style.display = 'none';
                    } else {
                        nutritionalInfo.style.display = 'block';
                        nutritionalInfo.style.whiteSpace = 'normal';
                    }
                }
            }
        });
    });
    
    // Handle mobile price toggles
    const priceHeaders = document.querySelectorAll('.mobile-prices-header');
    priceHeaders.forEach(header => {
        // Get the target collapse element ID
        const targetId = header.getAttribute('data-bs-target');
        if (targetId) {
            const target = document.querySelector(targetId);
            
            header.addEventListener('click', function() {
                // Toggle the collapsed class to rotate the chevron
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                
                if (isExpanded) {
                    this.classList.add('collapsed');
                    this.setAttribute('aria-expanded', 'false');
                    if (target) {
                        target.classList.remove('show');
                    }
                } else {
                    this.classList.remove('collapsed');
                    this.setAttribute('aria-expanded', 'true');
                    if (target) {
                        target.classList.add('show');
                    }
                }
            });
        }
    });
    
    // Add tooltip functionality for truncated text
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Initialize meal voting system
    initMealVoting();
    
    // SAMBALALARM - Check if any meal in XXXLutz Hesse Markrestaurant contains "Sambal"
    function checkForSambal() {
        // Check if we're on the XXXLutz Hesse Markrestaurant section
        const xxxlutzContainer = document.querySelector('.xxxlutz-container');
        if (xxxlutzContainer) {
            // Get all meal descriptions in the XXXLutz section
            const mealCards = xxxlutzContainer.querySelectorAll('.xxxlutz-card');
            
            // Check each meal description for "Sambal"
            let sambalFound = false;
            let sambalMealCard = null;
            
            mealCards.forEach(card => {
                const mealText = card.textContent.toLowerCase().trim();
                if (mealText.includes('sambal')) {
                    sambalFound = true;
                    // Highlight this specific meal card
                    card.classList.add('sambal-meal-card');
                    card.style.boxShadow = '0 0 15px 5px rgba(255, 0, 0, 0.7)';
                    card.style.animation = 'sambalPulse 0.8s infinite alternate';
                    sambalMealCard = card;
                }
            });
            
            // If Sambal was found, check if alarm should be shown
            // Only show the fullscreen alarm once per session (not on date changes)
            if (sambalFound) {
                const alarmShown = sessionStorage.getItem('sambalalarmShown');
                if (alarmShown === null) {
                    createFullscreenSambalalarm(sambalMealCard);
                    // Mark that the alarm has been shown in this session
                    sessionStorage.setItem('sambalalarmShown', 'true');
                }
            }
        }
    }
    
    // Function to create the fullscreen Sambalalarm
    function createFullscreenSambalalarm(sambalMealCard) {
        // Create the fullscreen sambalalarm element
        const sambalalarm = document.createElement('div');
        sambalalarm.className = 'fullscreen-sambalalarm';
        sambalalarm.id = 'fullscreen-sambalalarm';
        
        // Create container
        const container = document.createElement('div');
        container.className = 'sambalalarm-container';
        
        // Create main text
        const text = document.createElement('h1');
        text.className = 'sambalalarm-text';
        text.textContent = '🔥 SAMBAL ALARM!!! 🔥';
        
        // Add more floating fire emojis with varied sizes
        for (let i = 0; i < 50; i++) {
            const fireEmoji = document.createElement('div');
            fireEmoji.className = 'fire-emoji';
            fireEmoji.textContent = '🔥';
            
            // Random positioning
            fireEmoji.style.top = Math.random() * 100 + '%';
            fireEmoji.style.left = Math.random() * 100 + '%';
            
            // Random sizing
            const size = 2.5 + (Math.random() * 2);
            fireEmoji.style.fontSize = size + 'rem';
            
            // Randomize the starting point of the animation
            fireEmoji.style.animationDelay = (Math.random() * 3) + 's';
            
            sambalalarm.appendChild(fireEmoji);
        }
        
        // Assemble the elements
        container.appendChild(text);
        sambalalarm.appendChild(container);
        
        // Shared function to dismiss the sambalalarm with fade-out
        function dismissSambalalarm() {
            if (document.body.contains(sambalalarm)) {
                sambalalarm.style.opacity = '0';
                setTimeout(() => {
                    if (document.body.contains(sambalalarm)) {
                        document.body.removeChild(sambalalarm);
                    }
                }, 500);
            }
        }
        
        // Add click event to dismiss the alarm
        sambalalarm.addEventListener('click', dismissSambalalarm);
        
        // Add to DOM
        document.body.appendChild(sambalalarm);
        
        // Auto fade out after 4 seconds
        setTimeout(dismissSambalalarm, 4000);
        
        // Sound removed as requested
    }
    
    // Run the Sambal check when page loads
    setTimeout(checkForSambal, 500);
    
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
            expertModeToggleIcon.style.opacity = expertModeEnabled ? '1' : '0.5';
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

    // Removed initMealRecommendation() and getMealRecommendation() functions as they are deprecated

});

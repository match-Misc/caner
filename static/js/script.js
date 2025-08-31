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
    let dashboardModeEnabled = localStorage.getItem('dashboardMode') === 'enabled';

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
            
            // If Sambal was found, create and show the fullscreen Sambalalarm
            if (sambalFound) {
                createFullscreenSambalalarm(sambalMealCard);
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
        
        // Add click event to dismiss the alarm
        sambalalarm.addEventListener('click', function() {
            sambalalarm.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(sambalalarm);
            }, 500);
        });
        
        // Add to DOM
        document.body.appendChild(sambalalarm);
        
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
    

    // Removed initMealRecommendation() and getMealRecommendation() functions as they are deprecated

});

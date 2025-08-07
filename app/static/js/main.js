// app/static/js/main.js

// CSRF Token Auto-Refresh (prevents logout issues)
function refreshCSRFToken() {
    fetch('/api/csrf-token')
        .then(response => response.json())
        .then(data => {
            // Update all CSRF tokens on the page
            document.querySelectorAll('input[name="csrf_token"]').forEach(input => {
                input.value = data.csrf_token;
            });
            // Update meta tag if exists
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                metaTag.content = data.csrf_token;
            }
        })
        .catch(error => console.error('Error refreshing CSRF token:', error));
}

// Refresh CSRF token every 30 minutes
setInterval(refreshCSRFToken, 30 * 60 * 1000);

// Scripture Toggle
function toggleScripture() {
    const preview = document.getElementById('scripture-preview');
    const full = document.getElementById('scripture-full');
    const btn = document.getElementById('toggle-btn');
    
    if (full && full.style.display === 'none') {
        preview.style.display = 'none';
        full.style.display = 'inline';
        btn.textContent = 'show less';
    } else if (full) {
        preview.style.display = 'inline';
        full.style.display = 'none';
        btn.textContent = 'read more';
    }
}

// Audio Player Management
function initAudioPlayers() {
    const audioElements = document.querySelectorAll('audio');
    
    audioElements.forEach(audio => {
        audio.volume = 0.5; // Start at 50% volume
        
        // Pause other audio when starting a new one
        audio.addEventListener('play', function() {
            audioElements.forEach(otherAudio => {
                if (otherAudio !== audio) {
                    otherAudio.pause();
                }
            });
        });
    });
}

// Track Selection for Playlists
function selectAll() {
    document.querySelectorAll('.track-checkbox').forEach(cb => cb.checked = true);
}

function selectNone() {
    document.querySelectorAll('.track-checkbox').forEach(cb => cb.checked = false);
}

// Add to Playlist
function addToPlaylist() {
    const selectedTracks = document.querySelectorAll('.track-checkbox:checked');
    const playlistSelect = document.getElementById('playlist-select');
    
    if (selectedTracks.length === 0) {
        alert('Please select at least one track.');
        return false;
    }
    
    if (playlistSelect && !playlistSelect.value) {
        alert('Please select a playlist.');
        return false;
    }
    
    // Submit the form
    const form = document.getElementById('add-to-playlist-form');
    if (form && playlistSelect) {
        form.action = `/music/playlists/${playlistSelect.value}/add`;
        form.submit();
    }
}

// Auto-hide alerts after 5 seconds
function initAlerts() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-info)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initAudioPlayers();
    initAlerts();
});
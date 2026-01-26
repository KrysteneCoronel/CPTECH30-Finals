// Load reusable navigation component
function loadNavigation(currentPage) {
  // Navigation HTML template (inline to avoid CORS issues with file:// protocol)
  const navHTML = `
    <nav id="mainNav">
      <div class="logo">
        <span class="logo-text">KLIKSY</span><span class="logo-dot">.</span>
      </div>
      <div class="nav-links flex gap-2">
        <a href="feed.html" class="nav-link" data-page="feed">Feed</a>
        <a href="upload.html" class="nav-link" data-page="upload">Upload</a>
        <a href="profile.html" class="nav-link" data-page="profile">Profile</a>
      </div>
    </nav>
  `;
  
  // Insert nav at the beginning of body
  const navContainer = document.createElement('div');
  navContainer.innerHTML = navHTML;
  document.body.insertBefore(navContainer.firstElementChild, document.body.firstChild);
  
  // Set active nav link based on current page
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    if (link.dataset.page === currentPage) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

// Auto-load when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    // This will be called by individual pages
  });
}

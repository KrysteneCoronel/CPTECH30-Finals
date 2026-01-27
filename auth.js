(function () {
  const STORAGE_KEY = 'kliksyUser';
  const LOGOUT_ENDPOINT = 'https://hoev7s4i82.execute-api.us-east-1.amazonaws.com/logout';
  const PUBLIC_PAGES = new Set(['', 'index.html', 'sign_up.html']);
  const PROTECTED_PAGES = new Set(['feed.html', 'profile.html', 'upload.html']);

  const getCurrentPage = () => {
    const segments = window.location.pathname.split('/');
    const last = segments[segments.length - 1] || '';
    return last.toLowerCase();
  };

  const safeParseUser = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  };

  const redirectTo = (target) => {
    if (!target) {
      return;
    }
    const normalizedTarget = target.toLowerCase();
    if (getCurrentPage() === normalizedTarget) {
      return;
    }
    window.location.href = target;
  };

  const enforceAccess = () => {
    const page = getCurrentPage();
    const isLoggedIn = Boolean(safeParseUser());

    if (PROTECTED_PAGES.has(page) && !isLoggedIn) {
      redirectTo('index.html');
      return true;
    }

    if (PUBLIC_PAGES.has(page) && isLoggedIn) {
      redirectTo('feed.html');
      return true;
    }

    return false;
  };

  enforceAccess();
  window.addEventListener('pageshow', enforceAccess);

  window.kliksyAuth = {
    storageKey: STORAGE_KEY,
    get user() {
      return safeParseUser();
    },
    get isLoggedIn() {
      return Boolean(safeParseUser());
    },
    async logout(target = 'index.html') {
      const user = safeParseUser();

      if (LOGOUT_ENDPOINT && user) {
        try {
          await fetch(LOGOUT_ENDPOINT, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: user.email,
              username: user.username,
            }),
          });
        } catch (error) {
          console.warn('logout audit failed', error);
        }
      }

      localStorage.removeItem(STORAGE_KEY);
      redirectTo(target);
    }
  };
})();

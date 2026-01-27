(function () {
  const STORAGE_KEY = 'kliksyUser';
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

  const page = getCurrentPage();
  const user = safeParseUser();
  const isLoggedIn = Boolean(user);

  if (PROTECTED_PAGES.has(page) && !isLoggedIn) {
    redirectTo('index.html');
    return;
  }

  if (PUBLIC_PAGES.has(page) && isLoggedIn) {
    redirectTo('feed.html');
    return;
  }

  window.kliksyAuth = {
    storageKey: STORAGE_KEY,
    get user() {
      return safeParseUser();
    },
    get isLoggedIn() {
      return Boolean(safeParseUser());
    },
    logout(target = 'index.html') {
      localStorage.removeItem(STORAGE_KEY);
      redirectTo(target);
    }
  };
})();

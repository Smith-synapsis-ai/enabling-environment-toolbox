import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useState, useCallback, useEffect } from 'react';
import Header from './components/layout/Header';
import EmailCaptureModal from './components/common/EmailCaptureModal';
import PulseSurvey from './components/common/PulseSurvey';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import TutorialPage from './pages/TutorialPage';
import CatalogPage from './pages/CatalogPage';
import AdminPage from './pages/AdminPage';

/** Capture UTM parameters from the URL on first load and persist in sessionStorage. */
function captureUtmParams() {
  const params = new URLSearchParams(window.location.search);
  const utmKeys = ['utm_source', 'utm_medium', 'utm_campaign'] as const;
  for (const key of utmKeys) {
    const value = params.get(key);
    if (value) {
      sessionStorage.setItem(`ee-${key.replace('_', '-')}`, value);
    }
  }
}

function AppContent() {
  const location = useLocation();
  const [toolViewCount, setToolViewCount] = useState(0);
  const [searchPerformed, setSearchPerformed] = useState(false);

  // Capture UTM parameters once on mount
  useEffect(() => {
    captureUtmParams();
  }, []);

  const handleToolViewed = useCallback(() => {
    setToolViewCount(prev => prev + 1);
  }, []);

  const handleSearchPerformed = useCallback(() => {
    setSearchPerformed(true);
  }, []);

  return (
    <div className="min-h-screen">
      {/* Skip to content link for keyboard/screen reader users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[60] focus:bg-white focus:text-cgiar-dark focus:px-4 focus:py-2 focus:rounded-md focus:shadow-lg focus:text-sm focus:font-medium"
      >
        Skip to main content
      </a>

      {/* Header is always visible */}
      <Header />

      <main id="main-content">
        <Routes>
          <Route path="/" element={
            <HomePage
              onToolViewed={handleToolViewed}
              onSearchPerformed={handleSearchPerformed}
            />
          } />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/tutorial" element={<TutorialPage />} />
          <Route path="/catalog" element={<CatalogPage onToolViewed={handleToolViewed} />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>

      {/* Pulse Survey */}
      <PulseSurvey
        hasSearched={searchPerformed}
        hasViewedTool={toolViewCount > 0}
      />

      {/* Email capture modal */}
      <EmailCaptureModal toolViewCount={toolViewCount} />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

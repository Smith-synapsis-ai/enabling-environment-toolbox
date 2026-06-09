import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Image } from 'lucide-react';
import { useState } from 'react';

export default function Header() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [bgEnabled, setBgEnabled] = useState(() => {
    return localStorage.getItem('ee-bg-enabled') !== 'false';
  });

  const mainNavLinks = [
    { to: '/', label: 'Home' },
    { to: '/about', label: 'About' },
    { to: '/tutorial', label: 'Tutorial' },
  ];

  const isActive = (path: string) => location.pathname === path;

  const toggleBackground = () => {
    const newVal = !bgEnabled;
    setBgEnabled(newVal);
    localStorage.setItem('ee-bg-enabled', String(newVal));
    window.dispatchEvent(new Event('ee-bg-toggle'));
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-cgiar-dark/95 backdrop-blur-md border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-2 text-white hover:opacity-90 transition-opacity flex-shrink-0"
            aria-label="CGIAR Scaling for Impact - Home"
          >
            <img
              src="/branding/stacked-logo-white.svg"
              alt="CGIAR Scaling for Impact"
              className="h-8 sm:h-9"
            />
          </Link>

          {/* Desktop Nav — left cluster + right catalog pill */}
          <nav className="hidden md:flex items-center flex-1 ml-6" aria-label="Main navigation">
            {/* Left cluster: Home, About, Tutorial + bg toggle */}
            <div className="flex items-center gap-1">
              {mainNavLinks.map(link => (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(link.to)
                      ? 'text-white bg-white/10'
                      : 'text-white/80 hover:text-white hover:bg-white/5'
                  }`}
                  {...(isActive(link.to) ? { 'aria-current': 'page' as const } : {})}
                >
                  {link.label}
                </Link>
              ))}

              {/* Background image toggle */}
              <button
                onClick={toggleBackground}
                className="ml-1 p-2 rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
                aria-label={bgEnabled ? 'Disable background image' : 'Enable background image'}
                title={bgEnabled ? 'Disable background image' : 'Enable background image'}
              >
                <Image size={18} className={bgEnabled ? 'text-white/80' : 'text-white/40'} aria-hidden="true" />
              </button>
            </div>

            {/* Right side: Catalog pill button */}
            <Link
              to="/catalog"
              className={`ml-auto px-4 py-1.5 rounded-full border text-sm font-medium transition-all ${
                isActive('/catalog')
                  ? 'border-s4i-purple/60 bg-s4i-purple/15 text-white'
                  : 'border-white/30 text-white/90 hover:bg-white/10 hover:border-white/50'
              }`}
              {...(isActive('/catalog') ? { 'aria-current': 'page' as const } : {})}
            >
              Catalog
            </Link>
          </nav>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-white p-2"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-nav"
          >
            {mobileMenuOpen ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile Nav */}
      {mobileMenuOpen && (
        <div id="mobile-nav" className="md:hidden bg-cgiar-dark border-t border-white/10">
          <nav className="px-4 py-3 space-y-1" aria-label="Main navigation">
            {mainNavLinks.map(link => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive(link.to)
                    ? 'text-white bg-white/10'
                    : 'text-white/80 hover:text-white hover:bg-white/5'
                }`}
                {...(isActive(link.to) ? { 'aria-current': 'page' as const } : {})}
              >
                {link.label}
              </Link>
            ))}
            {/* Catalog with visual distinction in mobile too */}
            <Link
              to="/catalog"
              onClick={() => setMobileMenuOpen(false)}
              className={`block px-4 py-2.5 rounded-md text-sm font-medium transition-colors border ${
                isActive('/catalog')
                  ? 'text-white bg-s4i-purple/15 border-s4i-purple/40'
                  : 'text-white/80 hover:text-white hover:bg-white/5 border-white/20'
              }`}
              {...(isActive('/catalog') ? { 'aria-current': 'page' as const } : {})}
            >
              Catalog
            </Link>
            {/* Mobile bg toggle */}
            <button
              onClick={toggleBackground}
              className="w-full flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium text-white/70 hover:text-white hover:bg-white/5 transition-colors"
              aria-label={bgEnabled ? 'Disable background image' : 'Enable background image'}
            >
              <Image size={16} className={bgEnabled ? 'text-white/80' : 'text-white/40'} aria-hidden="true" />
              <span>{bgEnabled ? 'Hide background' : 'Show background'}</span>
            </button>
          </nav>
        </div>
      )}
    </header>
  );
}

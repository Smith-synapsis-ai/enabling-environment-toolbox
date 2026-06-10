import { Link, useLocation } from 'react-router-dom';
import { Leaf, Menu, X, Image } from 'lucide-react';
import { useState } from 'react';

export default function Header() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [bgEnabled, setBgEnabled] = useState(() => {
    return localStorage.getItem('ee-bg-enabled') !== 'false';
  });

  const navLinks = [
    { to: '/', label: 'Home' },
    { to: '/about', label: 'About' },
    { to: '/tutorial', label: 'Tutorial' },
    { to: '/catalog', label: 'Search by Catalog' },
    { to: '/assistant', label: 'Assistant' },
  ];

  const isActive = (path: string) => location.pathname === path;

  const toggleBackground = () => {
    const newVal = !bgEnabled;
    setBgEnabled(newVal);
    localStorage.setItem('ee-bg-enabled', String(newVal));
    window.dispatchEvent(new Event('ee-bg-toggle'));
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-cgiar-dark/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-white hover:opacity-90 transition-opacity" aria-label="CGIAR Enabling Environment Toolbox — Home">
            <Leaf size={24} className="text-cgiar-accent" aria-hidden="true" />
            <span className="text-lg font-bold tracking-wide">CGIAR</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navLinks.map(link => (
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
              className="ml-2 p-2 rounded-md text-white/60 hover:text-white hover:bg-white/10 transition-colors"
              aria-label={bgEnabled ? 'Disable background image' : 'Enable background image'}
              title={bgEnabled ? 'Disable background image' : 'Enable background image'}
            >
              <Image size={18} className={bgEnabled ? 'text-white/80' : 'text-white/40'} />
            </button>
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
            {navLinks.map(link => (
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
          </nav>
        </div>
      )}
    </header>
  );
}

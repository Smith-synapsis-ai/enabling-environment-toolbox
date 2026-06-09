import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Menu, X, Sparkles } from 'lucide-react'
import { useState } from 'react'

export function Navbar() {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  const links = [
    { to: '/', label: 'Home' },
    { to: '/explore', label: 'Explore' },
    { to: '/guide', label: 'AI Guide', icon: true },
    { to: '/about', label: 'About' },
  ]

  return (
    <nav className="bg-[#00524D] sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 flex-shrink-0">
          <img
            src="/images/cgiar-logo.png"
            alt="CGIAR Scaling for Impact"
            className="h-9 object-contain"
          />
          <span className="inline-flex items-center rounded-md px-1.5 py-0.5 text-[9px] font-bold tracking-widest uppercase bg-amber-400 text-amber-900 ml-1">
            BETA
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {links.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-1.5",
                location.pathname === link.to
                  ? "bg-white/15 text-white"
                  : "text-white/80 hover:text-white hover:bg-white/10"
              )}
            >
              {link.icon && <Sparkles size={14} />}
              {link.label}
            </Link>
          ))}
          <Link
            to="/explore"
            className="ml-4 px-4 py-2 bg-white text-[#00524D] rounded-lg text-sm font-semibold hover:bg-gray-50 transition-colors"
          >
            Explore Tools
          </Link>
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden text-white p-2"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-[#003D39] border-t border-white/10">
          {links.map(link => (
            <Link
              key={link.to}
              to={link.to}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors",
                location.pathname === link.to
                  ? "text-white bg-white/10"
                  : "text-white/80 hover:text-white hover:bg-white/5"
              )}
            >
              {link.icon && <Sparkles size={14} />}
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  )
}

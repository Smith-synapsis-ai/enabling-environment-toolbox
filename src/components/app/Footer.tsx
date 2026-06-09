import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="bg-[#00524D] text-white mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          <div>
            <img
              src="/images/cgiar-logo.png"
              alt="CGIAR Scaling for Impact"
              className="h-10 object-contain mb-4"
            />
            <p className="text-white/70 text-sm leading-relaxed">
              The Enabling Environment Toolbox is a knowledge platform developed by CGIAR to support
              agricultural innovation scaling through evidence and practical tools.
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4 text-sm uppercase tracking-wide">
              Navigation
            </h4>
            <ul className="space-y-2">
              {[
                { to: '/', label: 'Home' },
                { to: '/explore', label: 'Explore' },
                { to: '/guide', label: 'AI Guide' },
                { to: '/about', label: 'About' },
              ].map(link => (
                <li key={link.to}>
                  <Link
                    to={link.to}
                    className="text-white/70 text-sm hover:text-white transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-white mb-4 text-sm uppercase tracking-wide">
              Data Sources
            </h4>
            <ul className="space-y-2">
              {['CG Space', 'FAO', 'IFAD', 'World Bank', 'CGIAR Centers'].map(item => (
                <li key={item}>
                  <span className="text-white/70 text-sm cursor-pointer hover:text-white transition-colors">
                    {item}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-10 pt-6 border-t border-white/20 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-white/60 text-xs">
            &copy; 2026 CGIAR Scaling for Impact. All rights reserved.
          </p>
          <p className="text-white/60 text-xs">
            Enabling Environment Toolbox v2.0 Beta
          </p>
        </div>
      </div>
    </footer>
  )
}

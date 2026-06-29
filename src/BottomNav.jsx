import { Link, useLocation } from 'react-router-dom';

export default function BottomNav() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', icon: '💿', label: 'Albums' },
    { path: '/library?tab=artists', icon: '🎤', label: 'Artists' },
    { path: '/playlists', icon: '📻', label: 'Playlists' },
    { path: '/search', icon: '🔍', label: 'Search' },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 w-full bg-gray-900/95 border-t border-gray-800 backdrop-blur-lg z-40 pb-safe">
      <div className="flex justify-around items-center h-16">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link 
              key={item.path} 
              to={item.path}
              className={`flex flex-col items-center justify-center w-full h-full space-y-1 transition-colors ${
                isActive ? 'text-blue-400' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-[10px] font-medium tracking-wide">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
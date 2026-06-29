import { Link, useLocation } from 'react-router-dom';

export default function BottomNav() {
  const location = useLocation();
  
  // Removed Search, updated Artists path
  const navItems = [
    { path: '/', icon: '💿', label: 'Albums' },
    { path: '/library?tab=artists', icon: '🎤', label: 'Artists' },
    { path: '/playlists', icon: '📻', label: 'Playlists' },
  ];

  return (
    <nav className="md:hidden w-full h-[65px] bg-gray-900 border-t border-gray-800 shrink-0">
      <div className="flex justify-around items-center h-full px-2">
        {navItems.map((item) => {
          // Smart active state: checks both the pathname AND the query string
          const isActive = 
            location.pathname === item.path || 
            (location.pathname + location.search) === item.path;

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
import { Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import useScrollRestore from './useScrollRestore';
import SearchBar from './SearchBar';
import DiscoveryView from './DiscoveryView';
import AlbumPage from './AlbumPage';
import ArtistPage from './ArtistPage';
import AudioPlayer from './AudioPlayer';
import Settings from './Settings';

// A simple 404 component
function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-gray-400">
      <h2 className="text-4xl font-bold text-white mb-2">404</h2>
      <p>The media you are looking for does not exist.</p>
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const scrollRef = useScrollRestore();

  // Highlight "My Library" if we are anywhere inside the library, album, or artist routes
  const isLibraryActive = location.pathname.startsWith('/library') || 
                          location.pathname.startsWith('/album') || 
                          location.pathname.startsWith('/artist') ||
                          location.pathname === '/';

  const icons = { /* ... keep your existing SVG code for icons here ... */ };

  return (
    <div className="flex h-screen w-full bg-gray-950 text-gray-100 overflow-hidden font-sans">
      
      {/* DESKTOP SIDEBAR */}
      <nav className="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 shrink-0 z-20">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider text-blue-500">EcoGenious</h1>
        </div>

        <div className="flex-1 px-4 space-y-2 mt-4">
          <NavLink 
            to="/library"
            // Use a unique key based on location to force a full remount/refresh when clicking "My Library"
            key={location.pathname === '/library' ? Date.now() : 'lib'}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${isLibraryActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}
          >
            <span className="font-medium">My Library</span>
          </NavLink>
          
          <NavLink 
            to="/settings"
            className={({ isActive }) => `w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${isActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}
          >
            <span className="font-medium">Configuration</span>
          </NavLink>
        </div>
      </nav>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 relative h-full">
        <header className="shrink-0 h-20 bg-gray-950/80 backdrop-blur-md sticky top-0 z-10 flex items-center px-6 border-b border-gray-800/50">
          <div className="w-full max-w-2xl"><SearchBar /></div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="pb-32">
            <Routes>
              <Route path="/" element={<Navigate to="/library" replace />} />
              <Route path="/library" element={<DiscoveryView />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/album/:albumId" element={<AlbumPage />} />
              <Route path="/artist/:artistName" element={<ArtistPage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </div>
      </main>

      {/* MOBILE NAV */}
      <nav className="md:hidden fixed bottom-24 left-0 w-full bg-gray-900 border-t border-gray-800 z-20 flex justify-around items-center h-16 pb-safe">
          {/* Apply same NavLink logic here for mobile icons */}
      </nav>

      <div className="fixed bottom-0 left-0 w-full z-30">
        <AudioPlayer />
      </div>
    </div>
  );
}
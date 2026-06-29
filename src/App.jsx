import { Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import { usePlayerStore } from './store';
import useScrollRestore from './useScrollRestore';
import SearchBar from './SearchBar';
import DiscoveryView from './DiscoveryView';
import AlbumPage from './AlbumPage';
import ArtistPage from './ArtistPage';
import AudioPlayer from './AudioPlayer';
import Settings from './Settings';
import Playlists from './Playlists';
import QueueFlyout from './QueueFlyout';
import BottomNav from './BottomNav';

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
  const { currentTrack } = usePlayerStore();
  const hasTrack = currentTrack && Object.keys(currentTrack).length > 0;
  const paddingClass = hasTrack ? "pb-[130px] md:pb-24" : "pb-16 md:pb-0";
  const location = useLocation();
  const scrollRef = useScrollRestore();

  // Highlight "My Library" if we are anywhere inside the library, album, or artist routes
  const isLibraryActive = location.pathname.startsWith('/library') || 
                          location.pathname.startsWith('/album') || 
                          location.pathname.startsWith('/artist') ||
                          location.pathname === '/';

  const icons = { /* ... keep your existing SVG code for icons here ... */ };
  // Calculate exact padding dynamically
  // If playing: Mobile needs 130px (Nav + Player). Desktop needs 96px (Player only).
  // If empty: Mobile needs 64px (Nav only). Desktop needs 0px (Nothing).

  return (
    <div className="absolute inset-0 flex flex-col bg-black text-white overflow-hidden">
      
      {/* TOP SECTION: Sidebar + Main Scrollable Area */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Desktop Sidebar */}
        <aside className="hidden md:flex w-64 flex-col bg-gray-900 border-r border-gray-800 shrink-0">
      <nav className="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 shrink-0 z-20">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider text-blue-500">EcoGenious</h1>
        </div>

        <div className="flex-1 px-4 space-y-2 mt-4">
          <NavLink 
            to="/library?tab=albums" 
            className={({ isActive, search }) => `flex items-center space-x-3 p-3 rounded-lg font-medium transition-colors ${isActive && search === '?tab=albums' ? 'bg-blue-600/20 text-blue-500' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <span className="text-xl">💿</span>
            <span>Albums</span>
          </NavLink>

          <NavLink 
            to="/library?tab=artists" 
            className={({ isActive, search }) => `flex items-center space-x-3 p-3 rounded-lg font-medium transition-colors ${isActive && search === '?tab=artists' ? 'bg-blue-600/20 text-blue-500' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <span className="text-xl">🎤</span>
            <span>Artists</span>
          </NavLink>

          <NavLink 
            to="/playlists" 
            className={({ isActive, search }) => `flex items-center space-x-3 p-3 rounded-lg font-medium transition-colors ${isActive && search === '?tab=playlists' ? 'bg-blue-600/20 text-blue-500' : 'text-gray-400 hover:bg-gray-800 hover:text-white'}`}
          >
            <span className="text-xl">📻</span>
            <span>Playlists</span>
          </NavLink>
          
          <NavLink 
            to="/settings"
            className={({ isActive }) => `w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${isActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}
          >
            <span className="font-medium">Configuration</span>
          </NavLink>
        </div>
      </nav>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 overflow-y-auto relative bg-gradient-to-b from-gray-900 to-black">
        
        <header className="shrink-0 h-20 bg-gray-950/80 backdrop-blur-md sticky top-0 z-50 flex items-center px-6 border-b border-gray-800/50">
          <div className="w-full max-w-2xl"><SearchBar /></div>
        </header>

        <div id="main-scroll-container" ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar">
          <div className={`${paddingClass} min-h-full transition-all duration-300`}>
            <Routes>
              <Route path="/" element={<Navigate to="/library" replace />} />
              <Route path="/library" element={<DiscoveryView />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/album/:albumId" element={<AlbumPage />} />
              <Route path="/artist/:artistName" element={<ArtistPage />} />
              <Route path="/playlists" element={<Playlists />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </div>
      </main>
      </div>

      {/* BOTTOM SECTION: The Player and Mobile Nav automatically stack here */}
      <div className="flex flex-col shrink-0 z-40 bg-gray-900">
        <AudioPlayer />
        <BottomNav />
      </div>

      {/* Floating Elements */}
      <QueueFlyout />
      
    </div>
  );
}
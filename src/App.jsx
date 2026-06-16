import { useState } from 'react';
import SearchBar from './SearchBar';
import DiscoveryView from './DiscoveryView';
import AudioPlayer from './AudioPlayer';
import Settings from './Settings';

export default function App() {
  const [currentView, setCurrentView] = useState('library');

  // SVG Icons for Navigation
  const icons = {
    library: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
    settings: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    )
  };

  return (
    // The main container fills the viewport and prevents body scrolling
    <div className="flex h-screen w-full bg-gray-950 text-gray-100 overflow-hidden font-sans">
      
      {/* ==========================================
          DESKTOP SIDEBAR (Hidden on Mobile)
          ========================================== */}
      <nav className="hidden md:flex flex-col w-64 bg-gray-900 border-r border-gray-800 shrink-0 z-20">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider text-blue-500 flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
            </div>
            Audiophile Server by EcoGenius
          </h1>
        </div>

        <div className="flex-1 px-4 space-y-2 mt-4">
          <button 
            onClick={() => setCurrentView('library')}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${currentView === 'library' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}
          >
            {icons.library}
            <span className="font-medium">My Library</span>
          </button>
          
          <button 
            onClick={() => setCurrentView('settings')}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors ${currentView === 'settings' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}
          >
            {icons.settings}
            <span className="font-medium">Configuration</span>
          </button>
        </div>
      </nav>

      {/* ==========================================
          MAIN CONTENT AREA
          ========================================== */}
      <main className="flex-1 flex flex-col min-w-0 relative h-full">
        
        {/* Top Header & Global Search */}
        <header className="shrink-0 h-20 bg-gray-950/80 backdrop-blur-md sticky top-0 z-10 flex items-center px-6 md:px-12 border-b border-gray-800/50">
          <div className="w-full max-w-2xl">
            <SearchBar />
          </div>
        </header>

        {/* Scrollable Content View */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="pb-32"> {/* Padding to prevent content from hiding behind the audio player */}
            {currentView === 'library' && <DiscoveryView />}
            {currentView === 'settings' && <Settings />}
          </div>
        </div>
      </main>

      {/* ==========================================
          MOBILE BOTTOM NAVIGATION (Hidden on Desktop)
          ========================================== */}
      <nav className="md:hidden fixed bottom-24 left-0 w-full bg-gray-900 border-t border-gray-800 z-20 flex justify-around items-center h-16 pb-safe">
        <button 
          onClick={() => setCurrentView('library')}
          className={`flex flex-col items-center justify-center w-full h-full ${currentView === 'library' ? 'text-blue-500' : 'text-gray-400'}`}
        >
          {icons.library}
          <span className="text-[10px] mt-1 font-medium">Library</span>
        </button>
        <button 
          onClick={() => setCurrentView('settings')}
          className={`flex flex-col items-center justify-center w-full h-full ${currentView === 'settings' ? 'text-blue-500' : 'text-gray-400'}`}
        >
          {icons.settings}
          <span className="text-[10px] mt-1 font-medium">Settings</span>
        </button>
      </nav>

      {/* ==========================================
          PERSISTENT AUDIO PLAYER
          ========================================== */}
      {/* This component is absolutely positioned at the bottom of the viewport so it never scrolls away */}
      <div className="fixed bottom-0 left-0 w-full z-30">
        <AudioPlayer />
      </div>

    </div>
  );
}
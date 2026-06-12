import { useState, useEffect, useRef } from 'react';
import { usePlayerStore } from './store';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  
  const searchContainerRef = useRef(null);
  const playTrack = usePlayerStore(state => state.playTrack);

  // 1. Debounce Logic: Wait 300ms after the last keystroke
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(handler);
  }, [query]);

  // 2. Fetch Logic: Triggered only when debouncedQuery changes
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults(null);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    fetch(`/api/search?q=${encodeURIComponent(debouncedQuery)}`)
      .then(res => res.json())
      .then(data => {
        setResults(data);
        setIsSearching(false);
        setIsOpen(true);
      })
      .catch(err => {
        console.error("Search failed:", err);
        setIsSearching(false);
      });
  }, [debouncedQuery]);

  // 3. Click Outside Logic: Close dropdown if user clicks away
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Format duration helper (e.g., 234 -> 3:54)
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const handlePlay = (track) => {
    playTrack(track);
    setIsOpen(false); // Close search when playback starts
    setQuery(''); // Optional: clear search
  };

  return (
    <div className="relative w-full max-w-2xl mx-auto z-50" ref={searchContainerRef}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (results) setIsOpen(true); }}
          placeholder="Search for artists, albums, or songs..."
          className="block w-full pl-10 pr-3 py-3 border border-gray-700 rounded-full leading-5 bg-gray-900 text-gray-100 placeholder-gray-400 focus:outline-none focus:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200"
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && results && (
        <div className="absolute mt-2 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden max-h-[70vh] overflow-y-auto">
          
          {/* Tracks Section */}
          {results.tracks && results.tracks.length > 0 ? (
            <div className="p-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Songs</h3>
              <ul>
                {results.tracks.map((track) => (
                  <li key={track.id}>
                    <button 
                      onClick={() => handlePlay(track)}
                      className="w-full text-left px-2 py-2 flex items-center hover:bg-gray-800 rounded group transition-colors duration-150"
                    >
                      {/* Album Art Thumbnail */}
                      <div className="flex-shrink-0 h-10 w-10 relative bg-gray-800 rounded overflow-hidden mr-3">
                        {track.art ? (
                          <img src={`/art/${track.art}`} alt="" className="object-cover h-full w-full" />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center text-gray-600">🎵</div>
                        )}
                        {/* Play overlay on hover */}
                        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <svg className="h-5 w-5 text-white pl-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>
                      
                      {/* Track Details */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-100 truncate">{track.title}</p>
                        <p className="text-xs text-gray-400 truncate">{track.artist} &bull; {track.album}</p>
                      </div>
                      
                      {/* Duration */}
                      <div className="ml-4 flex-shrink-0 text-xs text-gray-500 group-hover:text-gray-300">
                        {formatTime(track.duration)}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            !isSearching && query && (
              <div className="p-4 text-center text-gray-400 text-sm">
                No results found for "{query}"
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
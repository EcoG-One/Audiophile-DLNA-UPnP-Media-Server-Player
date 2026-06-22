import { useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { usePlayerStore } from './store';
import FormattedTitle from './FormattedTitle';

export default function SearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [results, setResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  
  const searchContainerRef = useRef(null);
  const playTrack = usePlayerStore(state => state.playTrack);

  // Debounce keystrokes
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(handler);
  }, [query]);

  // Fetch from the new comprehensive API
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
      .catch(() => setIsSearching(false));
  }, [debouncedQuery]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // --- Click Handlers ---
  const handlePlay = (track) => {
    playTrack(track);
    setIsOpen(false);
  };

  const handleNavigate = (type, id) => {
    setIsOpen(false);
    setQuery('');
    
    // Push directly to the URL!
    if (type === 'album') navigate(`/album/${encodeURIComponent(id)}`);
    if (type === 'artist') navigate(`/artist/${encodeURIComponent(id)}`);
  };

  // Helper to check if we have any results at all
  const hasResults = results && (results.tracks.length > 0 || results.albums.length > 0 || results.artists.length > 0);

  return (
    <div className="relative w-full max-w-2xl mx-auto z-50" ref={searchContainerRef}>
      {/* Input Field */}
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
          onFocus={() => { if (hasResults) setIsOpen(true); }}
          placeholder="Search for artists, albums, or songs..."
          className="block w-full pl-10 pr-3 py-3 border border-gray-700 rounded-full leading-5 bg-gray-900 text-gray-100 placeholder-gray-400 focus:outline-none focus:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200"
        />
        {isSearching && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          </div>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && results && (
        <div className="absolute mt-2 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden max-h-[75vh] overflow-y-auto custom-scrollbar">
          
          {hasResults ? (
            <div className="py-2">
              
              {/* --- ARTISTS SECTION --- */}
              {results.artists.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-4">Artists</h3>
                  <ul>
                    {results.artists.map(artist => (
                      <li key={`art-${artist.name}`}>
                        <button onClick={() => handleNavigate('artist', artist.name)} className="w-full text-left px-4 py-2 flex items-center hover:bg-gray-800 transition-colors">
                          <div className="h-10 w-10 rounded-full bg-gray-800 flex items-center justify-center mr-3 text-lg border border-gray-700">🎤</div>
                          <div>
                            <p className="text-sm font-medium text-gray-100">{artist.name}</p>
                            <p className="text-xs text-gray-400">{artist.album_count} Album{artist.album_count !== 1 ? 's' : ''}</p>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* --- ALBUMS SECTION --- */}
              {results.albums.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-4">Albums</h3>
                  <ul>
                    {results.albums.map(album => (
                      <li key={`alb-${album.id}`}>
                        <button onClick={() => handleNavigate('album', album.id)} className="w-full text-left px-4 py-2 flex items-center hover:bg-gray-800 transition-colors">
                          <div className="h-10 w-10 rounded bg-gray-800 mr-3 overflow-hidden border border-gray-700">
                            {album.art_hash ? <img src={`/art/${album.art_hash}`} className="w-full h-full object-cover" /> : <div className="w-full h-full flex items-center justify-center">💿</div>}
                          </div>
                          <div className="font-medium text-white truncate" title={album.title}>
                            <FormattedTitle title={album.title} />
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* --- SONGS SECTION --- */}
              {results.tracks.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-4">Songs</h3>
                  <ul>
                    {results.tracks.map((track) => (
                      <li key={`trk-${track.id}`}>
                        <button onClick={() => handlePlay(track)} className="w-full text-left px-4 py-2 flex items-center hover:bg-gray-800 group transition-colors">
                          <div className="h-10 w-10 relative bg-gray-800 rounded overflow-hidden mr-3 border border-gray-700">
                            {track.art ? <img src={`/art/${track.art}`} className="object-cover h-full w-full" /> : <div className="h-full w-full flex items-center justify-center">🎵</div>}
                            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                              <svg className="h-5 w-5 text-white pl-0.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" /></svg>
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-100 truncate group-hover:text-blue-400">{track.title}</p>
                            <p className="text-xs text-gray-400 truncate">{track.artist} &bull; {track.album}</p>
                          </div>
                          <div className="ml-4 text-xs text-gray-500">{formatTime(track.duration)}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            </div>
          ) : (
            !isSearching && query && (
              <div className="p-6 text-center text-gray-400 text-sm">
                No results found for "{query}"
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
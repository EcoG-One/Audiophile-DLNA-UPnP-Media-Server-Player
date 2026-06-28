import { useState, useEffect } from 'react';

export default function AddToPlaylistModal({ trackId, onClose }) {
  const [playlists, setPlaylists] = useState([]);
  const [newPlaylistName, setNewPlaylistName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetch('/api/playlists')
      .then(res => res.json())
      .then(data => setPlaylists(data))
      .catch(err => console.error("Failed to load playlists:", err));
  }, []);

  const handleAddToPlaylist = async (playlistId) => {
    try {
      await fetch(`/api/playlists/${playlistId}/tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track_id: trackId })
      });
      onClose(); // Close modal on success
    } catch (err) {
      console.error("Failed to add track:", err);
    }
  };

  const handleCreateAndAdd = async (e) => {
    e.preventDefault();
    if (!newPlaylistName.trim()) return;
    
    setIsCreating(true);
    try {
      // 1. Create the playlist
      const createRes = await fetch('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPlaylistName })
      });
      const newPlaylist = await createRes.json();

      // 2. Add the track to it
      await handleAddToPlaylist(newPlaylist.id);
    } catch (err) {
      console.error("Failed to create playlist:", err);
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center animate-fade-in p-4" onClick={onClose}>
      <div 
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()} // Prevent closing when clicking inside
      >
        <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
          <h3 className="text-lg font-bold text-gray-200">Add to Playlist</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">✕</button>
        </div>

        <div className="p-4 max-h-64 overflow-y-auto">
          {playlists.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">No playlists yet.</p>
          ) : (
            <ul className="space-y-1">
              {playlists.map(pl => (
                <li key={pl.id}>
                  <button 
                    onClick={() => handleAddToPlaylist(pl.id)}
                    className="w-full text-left px-3 py-2 rounded hover:bg-blue-600/20 hover:text-blue-400 text-gray-300 transition-colors flex items-center"
                  >
                    <span className="mr-3 text-gray-500">🎵</span> {pl.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="p-4 border-t border-gray-800 bg-gray-800/30">
          <form onSubmit={handleCreateAndAdd} className="flex gap-2">
            <input 
              type="text" 
              value={newPlaylistName}
              onChange={e => setNewPlaylistName(e.target.value)}
              placeholder="New playlist name..."
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              autoFocus
            />
            <button 
              type="submit" 
              disabled={isCreating || !newPlaylistName.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Create
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
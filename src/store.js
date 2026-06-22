import { create } from 'zustand';

export const usePlayerStore = create((set) => ({
  currentTrack: null,
  playlist: [],
  isPlaying: false,
  volume: 1.0,
  // New state for progress bar
  currentTime: 0,
  duration: 0,
  
  playTrack: (track) => set({ currentTrack: track, isPlaying: true }),
  setPlaylist: (tracks) => set({ playlist: tracks }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setVolume: (level) => set({ volume: level }),
  
  // New actions to update progress
  setTrackProgress: (currentTime, duration) => set({ currentTime, duration }),
  seekTo: (time) => set({ currentTime: time }),

  nextTrack: () => set((state) => {
    const currentIndex = state.playlist.findIndex(t => t.id === state.currentTrack?.id);
    if (currentIndex >= 0 && currentIndex < state.playlist.length - 1) {
        return { currentTrack: state.playlist[currentIndex + 1], isPlaying: true };
    }
    return state;
  })
}));

export const useLibraryStore = create((set, get) => ({
  albums: [],
  artists: [],
  albumsLoaded: false,
  artistsLoaded: false,

  fetchAlbums: async () => {
    if (get().albumsLoaded) return; // Prevent re-fetching if already cached
    try {
      const res = await fetch('/api/albums');
      const data = await res.json();
      set({ albums: data, albumsLoaded: true });
    } catch (err) {
      console.error("Failed to fetch albums:", err);
    }
  },

  fetchArtists: async () => {
    if (get().artistsLoaded) return; // Prevent re-fetching if already cached
    try {
      const res = await fetch('/api/artists');
      const data = await res.json();
      set({ artists: data, artistsLoaded: true });
    } catch (err) {
      console.error("Failed to fetch artists:", err);
    }
  }
}));

import { create } from 'zustand';

export const usePlayerStore = create((set, get) => ({
  currentTrack: null,
  playlist: [],
  isPlaying: false,
  volume: 1.0,
  // New state for progress bar
  currentTime: 0,
  duration: 0,
  
  // Queue System
  queue: [],
  queueIndex: -1,

  // Play a single track (bypassing the queue)
  playTrack: (track) => set({ currentTrack: track, isPlaying: true }),

  // Load an entire playlist into the queue
  setPlaylist: (tracks, startIndex = 0) => set({
    queue: tracks,
    queueIndex: startIndex,
    currentTrack: tracks[startIndex],
    isPlaying: true
  }),
  setVolume: (level) => set({ volume: level }),
  
  // actions to update progress
  setTrackProgress: (currentTime, duration) => set({ currentTime, duration }),
  seekTo: (time) => set({ currentTime: time }),

  // Skip Forward
  playNextTrack: () => {
    const { queue, queueIndex } = get();
    // Check if we have a queue and aren't at the end
    if (queue.length > 0 && queueIndex < queue.length - 1) {
      const nextIndex = queueIndex + 1;
      set({
        queueIndex: nextIndex,
        currentTrack: queue[nextIndex],
        isPlaying: true
      });
    } else {
      // Playlist finished
      set({ isPlaying: false });
    }
  },

  // Skip Backward
  playPreviousTrack: () => {
    const { queue, queueIndex } = get();
    if (queue.length > 0 && queueIndex > 0) {
      const prevIndex = queueIndex - 1;
      set({
        queueIndex: prevIndex,
        currentTrack: queue[prevIndex],
        isPlaying: true
      });
    }
  },

  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
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

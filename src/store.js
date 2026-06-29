import { create } from 'zustand';

export const usePlayerStore = create((set, get) => ({
  currentTrack: null,
  playlist: [],
  isPlaying: false,
  volume: 1.0,
  // State for progress bar
  currentTime: 0,
  duration: 0,
  
  // Queue System
  queue: [],
  queueIndex: -1,

  // Universal context tracking
  // Example: { type: 'playlist', id: '123' } or { type: 'album', id: '456' }
  playbackContext: null,

  playTrack: (track, context = null) => set({
    currentTrack: track,
    isPlaying: true,
    playbackContext: context
  }),

  setPlaylist: (tracks, startIndex = 0, context = null) => set({
    queue: tracks,
    queueIndex: startIndex,
    currentTrack: tracks[startIndex],
    isPlaying: true,
    playbackContext: context // Inject the context here
  }),
  setVolume: (level) => set({ volume: level }),

  // Add a single track to the end of the queue
  addToQueue: (track) => set((state) => {
    // If nothing is playing at all, just treat it like a normal play command
    if (!state.currentTrack) {
      return {
        queue: [track],
        queueIndex: 0,
        currentTrack: track,
        isPlaying: true
      };
    }

    // Otherwise, safely append it to the end of the existing queue
    return {
      queue: [...state.queue, track]
    };
  }),
  
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

  // Queue UI State
  isQueueFlyoutOpen: false,
  toggleQueueFlyout: () => set((state) => ({ isQueueFlyoutOpen: !state.isQueueFlyoutOpen })),

  // Jump to a specific track in the existing queue
  jumpToQueueIndex: (index) => set((state) => {
    if (index >= 0 && index < state.queue.length) {
      return {
        queueIndex: index,
        currentTrack: state.queue[index],
        isPlaying: true
      };
    }
    return state;
  }),

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



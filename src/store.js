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

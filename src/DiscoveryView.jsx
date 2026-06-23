import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useLibraryStore } from './store';
import AlbumGrid from './AlbumGrid';
import ArtistGrid from './ArtistGrid';
import ScrollToTopButton from './ScrollToTopButton';

export default function DiscoveryView() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'albums';

  const { albums, artists, fetchAlbums, fetchArtists, albumsLoaded, artistsLoaded } = useLibraryStore();

  useEffect(() => {
    if (activeTab === 'albums') fetchAlbums();
    if (activeTab === 'artists') fetchArtists();
  }, [activeTab, fetchAlbums, fetchArtists]);

  const isLoading = activeTab === 'albums' ? !albumsLoaded : !artistsLoaded;
  const items = activeTab === 'albums' ? albums : artists;

  return (
    <div className="w-full max-w-screen-2xl mx-auto px-6 py-8 pb-32 animate-fade-in relative">
      
      {/* Streamlined Header */}
      <div className="mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-4xl font-extrabold tracking-tight text-white capitalize">
          {activeTab}
        </h1>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-pulse flex space-x-4">
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
            <div className="w-12 h-12 bg-gray-800 rounded-full"></div>
          </div>
        </div>
      ) : (
        /* Render Grids */
        activeTab === 'albums' 
          ? <AlbumGrid albums={items} onAlbumClick={(id) => navigate(`/album/${encodeURIComponent(id)}`)} /> 
          : <ArtistGrid artists={items} onArtistClick={(name) => navigate(`/artist/${encodeURIComponent(name)}`)} />
      )}

      {/* The Floating Top Button */}
      <ScrollToTopButton />
    </div>
  );
}
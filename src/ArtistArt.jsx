import { useState, useEffect } from 'react';

export default function ArtistArtBanner({ artistName = "Daft Punk" }) {
  const [mediaAssets, setMediaAssets] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`http://127.0.0{encodeURIComponent(artistName)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch artist assets");
        return res.json();
      })
      .then((data) => {
        setMediaAssets(data.images);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [artistName]);

  if (loading) return <div className="text-white p-4">Loading artist media...</div>;
  if (error) return <div className="text-red-500 p-4">Error: {error}</div>;

  const backgroundUrl = mediaAssets?.background; // Points to local static file mount
  const logoUrl = mediaAssets?.logo;
  const thumbUrl = mediaAssets?.thumbnail;


  return (
    <div className="w-full max-w-4xl mx-auto bg-zinc-900 rounded-xl overflow-hidden shadow-2xl">
      {/* 16:9 Media Center Hero Background */}
      <div 
        className="relative h-64 sm:h-96 w-full bg-cover bg-center flex items-end p-6 transition-all duration-500"
        style={{ 
          backgroundImage: backgroundUrl ? `url(${backgroundUrl})` : 'none',
          backgroundColor: '#18181b' 
        }}
      >
        {/* Subtle dark gradient overlay to make text/logos pop */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* Dynamic UI Content overlay */}
        <div className="relative z-10 w-full flex items-center justify-between">
          {logoUrl ? (
            /* Render clear transparent text logo if it exists */
            <img src={logoUrl} alt={artistName} className="h-16 sm:h-24 object-contain max-w-[60%]" />
          ) : (
            /* Fallback to standard textual header if no logo asset exists */
            <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight">{artistName}</h1>
          )}

          {/* Square Artist profile badge in corner */}
          {thumbUrl && (
            <img 
              src={thumbUrl} 
              alt="" 
              className="w-20 h-20 sm:w-28 sm:h-28 rounded-full border-4 border-zinc-900 object-cover shadow-lg"
            />
          )}
        </div>
      </div>
    </div>
  );
}

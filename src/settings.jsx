import { useState, useEffect } from 'react';

export default function Settings() {
  const [config, setConfig] = useState({ BIND_IP: '', PORT: 8080, MEDIA_DIRS: [] });
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => setConfig(data));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setStatus('Saving...');
    
    // Basic Frontend Validation
    if (!config.BIND_IP.match(/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/)) {
        setStatus('Error: Invalid IP Address format.');
        return;
    }

    const response = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    if (response.ok) {
        setStatus('Configuration saved successfully! Server is rescanning.');
    } else {
        setStatus('Failed to save configuration.');
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto text-white">
      <h2 className="text-3xl font-bold mb-6 border-b border-gray-700 pb-2">Server Configuration</h2>
      
      <form onSubmit={handleSave} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-400">Bind IP Address</label>
          <input 
            type="text" 
            value={config.BIND_IP}
            onChange={e => setConfig({...config, BIND_IP: e.target.value})}
            className="mt-1 block w-full bg-gray-800 border border-gray-600 rounded-md p-2 text-white focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400">Port</label>
          <input 
            type="number" 
            value={config.PORT}
            onChange={e => setConfig({...config, PORT: parseInt(e.target.value)})}
            className="mt-1 block w-full bg-gray-800 border border-gray-600 rounded-md p-2 text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Media Directories</label>
          <textarea
            rows="3"
            value={config.MEDIA_DIRS.join('\n')}
            onChange={e => setConfig({...config, MEDIA_DIRS: e.target.value.split('\n')})}
            className="w-full bg-gray-800 border border-gray-600 rounded-md p-2 text-white text-sm font-mono"
            placeholder="/path/to/music"
          />
          <p className="text-xs text-gray-500 mt-1">Place each directory path on a new line.</p>
        </div>

        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Save Configuration
        </button>
        
        {status && <p className="mt-4 text-sm font-semibold text-blue-400">{status}</p>}
      </form>
    </div>
  );
}
import { useState } from 'react';
import './App.css';

interface VideoStream {
  mediaUrl: string;
  backupUrls?: string[];
  qualityType?: string;
  videoBitrate?: number;
  videoCodec?: string;
  width?: number;
  height?: number;
}

interface VideoInfo {
  title: string;
  description: string;
  author: string;
  duration: number;
  streams: VideoStream[];
  thumbnail?: string;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatQuality(stream: VideoStream): string {
  const parts: string[] = [];
  if (stream.width && stream.height) {
    parts.push(`${stream.width}x${stream.height}`);
  }
  if (stream.videoCodec) {
    parts.push(stream.videoCodec.toUpperCase());
  }
  if (stream.videoBitrate) {
    parts.push(`${Math.round(stream.videoBitrate / 1000)}kbps`);
  }
  return parts.length > 0 ? parts.join(' - ') : 'Standard Quality';
}

function App() {
  const [url, setUrl] = useState('');
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setVideoInfo(null);

    try {
      const response = await fetch('/api/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to extract video');
      }

      setVideoInfo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (stream: VideoStream) => {
    if (!videoInfo) return;

    setDownloading(true);
    try {
      // Create a safe filename from the title
      const safeTitle = videoInfo.title
        .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\s-]/g, '')
        .trim()
        .slice(0, 50) || 'video';
      const filename = `${safeTitle}.mp4`;

      // Use the proxy endpoint for download
      const downloadUrl = `/api/download?url=${encodeURIComponent(stream.mediaUrl)}&filename=${encodeURIComponent(filename)}`;

      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>RedNote Video Downloader</h1>
        <p className="subtitle">Download videos from Xiaohongshu / RedNote</p>
      </header>

      <main className="main">
        <form onSubmit={handleSubmit} className="url-form">
          <div className="input-group">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste your RedNote video link here (xhslink.com or xiaohongshu.com)"
              className="url-input"
              disabled={loading}
            />
            <button type="submit" className="submit-btn" disabled={loading || !url.trim()}>
              {loading ? 'Extracting...' : 'Get Video'}
            </button>
          </div>
        </form>

        {error && (
          <div className="error-box">
            <strong>Error:</strong> {error}
          </div>
        )}

        {videoInfo && (
          <div className="video-result">
            <div className="video-info">
              {videoInfo.thumbnail && (
                <img src={videoInfo.thumbnail} alt="Thumbnail" className="thumbnail" />
              )}
              <div className="video-details">
                <h2 className="video-title">{videoInfo.title}</h2>
                <p className="video-author">By {videoInfo.author}</p>
                {videoInfo.duration > 0 && (
                  <p className="video-duration">Duration: {formatDuration(videoInfo.duration)}</p>
                )}
                {videoInfo.description && (
                  <p className="video-description">{videoInfo.description}</p>
                )}
              </div>
            </div>

            <div className="streams-section">
              <h3>Available Downloads</h3>
              <div className="streams-list">
                {videoInfo.streams.map((stream, index) => (
                  <button
                    key={index}
                    className="stream-btn"
                    onClick={() => handleDownload(stream)}
                    disabled={downloading}
                  >
                    <span className="stream-quality">{formatQuality(stream)}</span>
                    <span className="download-icon">Download</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="instructions">
          <h3>How to use:</h3>
          <ol>
            <li>Open the RedNote (Xiaohongshu) app on your phone</li>
            <li>Find a video you want to download</li>
            <li>Tap the share button and copy the link</li>
            <li>Paste the link above and click "Get Video"</li>
            <li>Choose your preferred quality and download</li>
          </ol>
        </div>
      </main>

      <footer className="footer">
        <p>For personal use only. Please respect content creators' rights.</p>
      </footer>
    </div>
  );
}

export default App;

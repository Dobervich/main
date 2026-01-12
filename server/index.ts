import express from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Browser-like headers to avoid bot detection
const BROWSER_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  'Accept-Encoding': 'gzip, deflate, br',
  'Cache-Control': 'no-cache',
  'Pragma': 'no-cache',
};

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

// Follow redirects and get final URL
async function resolveShortUrl(url: string): Promise<string> {
  try {
    const response = await fetch(url, {
      method: 'HEAD',
      redirect: 'follow',
      headers: BROWSER_HEADERS,
    });
    return response.url;
  } catch {
    // If HEAD fails, try GET
    const response = await fetch(url, {
      redirect: 'follow',
      headers: BROWSER_HEADERS,
    });
    return response.url;
  }
}

// Extract __INITIAL_STATE__ JSON from HTML
function extractInitialState(html: string): Record<string, unknown> | null {
  // Look for window.__INITIAL_STATE__ = {...}
  const patterns = [
    /window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]*?\})\s*(?:;|<\/script>)/,
    /window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*;?\s*(?:window\.|<)/,
  ];

  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match?.[1]) {
      try {
        return JSON.parse(match[1]);
      } catch {
        continue;
      }
    }
  }

  // Try a more lenient extraction - find the JSON blob between script tags
  const scriptMatch = html.match(/<script[^>]*>[\s\S]*?window\.__INITIAL_STATE__\s*=\s*([\s\S]*?)<\/script>/);
  if (scriptMatch?.[1]) {
    // Find the JSON object start and match braces
    const jsonStr = scriptMatch[1].trim();
    if (jsonStr.startsWith('{')) {
      let braceCount = 0;
      let endIndex = 0;
      for (let i = 0; i < jsonStr.length; i++) {
        if (jsonStr[i] === '{') braceCount++;
        if (jsonStr[i] === '}') braceCount--;
        if (braceCount === 0) {
          endIndex = i + 1;
          break;
        }
      }
      if (endIndex > 0) {
        try {
          return JSON.parse(jsonStr.slice(0, endIndex));
        } catch {
          // Continue to next attempt
        }
      }
    }
  }

  return null;
}

// Extract post ID from URL
function extractPostId(url: string): string | null {
  // Match patterns like /explore/ID or /discovery/item/ID
  const patterns = [
    /\/explore\/([a-f0-9]{24})/i,
    /\/discovery\/item\/([a-f0-9]{24})/i,
    /\/item\/([a-f0-9]{24})/i,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }
  return null;
}

// Extract video info from the initial state
function extractVideoInfo(state: Record<string, unknown>, postId: string): VideoInfo | null {
  try {
    // Navigate the nested structure: note.noteDetailMap[postId].note
    const noteDetailMap = (state as { note?: { noteDetailMap?: Record<string, { note?: unknown }> } })
      ?.note?.noteDetailMap;

    if (!noteDetailMap) {
      console.log('No noteDetailMap found');
      return null;
    }

    // Try to find the note with the post ID or the first available note
    let noteData = noteDetailMap[postId]?.note as Record<string, unknown> | undefined;

    if (!noteData) {
      // Try to get the first note in the map
      const keys = Object.keys(noteDetailMap);
      if (keys.length > 0) {
        noteData = noteDetailMap[keys[0]]?.note as Record<string, unknown> | undefined;
      }
    }

    if (!noteData) {
      console.log('No note data found');
      return null;
    }

    // Extract video data
    const video = noteData.video as Record<string, unknown> | undefined;
    if (!video) {
      console.log('No video data found - this might be an image post');
      return null;
    }

    const media = video.media as Record<string, unknown> | undefined;
    const stream = media?.stream as Record<string, VideoStream[]> | undefined;

    if (!stream) {
      console.log('No stream data found');
      return null;
    }

    // Collect all available streams
    const streams: VideoStream[] = [];

    // Stream is usually organized by codec (h264, h265, av1)
    for (const [codec, codecStreams] of Object.entries(stream)) {
      if (Array.isArray(codecStreams)) {
        for (const s of codecStreams) {
          if (s.mediaUrl) {
            streams.push({
              mediaUrl: s.mediaUrl,
              backupUrls: s.backupUrls,
              qualityType: s.qualityType,
              videoBitrate: s.videoBitrate,
              videoCodec: codec,
              width: s.width,
              height: s.height,
            });
          }
        }
      }
    }

    if (streams.length === 0) {
      console.log('No valid streams found');
      return null;
    }

    // Sort by quality (higher resolution first)
    streams.sort((a, b) => {
      const aRes = (a.width || 0) * (a.height || 0);
      const bRes = (b.width || 0) * (b.height || 0);
      return bRes - aRes;
    });

    // Extract metadata
    const title = (noteData.title as string) || (noteData.desc as string) || 'Untitled';
    const description = (noteData.desc as string) || '';
    const user = noteData.user as Record<string, unknown> | undefined;
    const author = (user?.nickname as string) || (user?.name as string) || 'Unknown';
    const duration = (video.duration as number) || 0;

    // Get thumbnail
    const imageList = noteData.imageList as Array<{ urlDefault?: string }> | undefined;
    const thumbnail = imageList?.[0]?.urlDefault;

    return {
      title,
      description,
      author,
      duration,
      streams,
      thumbnail,
    };
  } catch (error) {
    console.error('Error extracting video info:', error);
    return null;
  }
}

// API endpoint to extract video info
app.post('/api/extract', async (req, res) => {
  const { url } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'URL is required' });
  }

  // Validate URL format
  if (!url.includes('xhslink.com') && !url.includes('xiaohongshu.com')) {
    return res.status(400).json({
      error: 'Invalid URL. Please provide a RedNote/Xiaohongshu share link.'
    });
  }

  try {
    console.log('Processing URL:', url);

    // Step 1: Resolve short URL to full URL
    let fullUrl = url;
    if (url.includes('xhslink.com')) {
      console.log('Resolving short URL...');
      fullUrl = await resolveShortUrl(url);
      console.log('Resolved to:', fullUrl);
    }

    // Step 2: Extract post ID
    const postId = extractPostId(fullUrl);
    if (!postId) {
      return res.status(400).json({
        error: 'Could not extract post ID from URL'
      });
    }
    console.log('Post ID:', postId);

    // Step 3: Fetch the page HTML
    console.log('Fetching page HTML...');
    const pageResponse = await fetch(fullUrl, {
      headers: BROWSER_HEADERS,
    });

    if (!pageResponse.ok) {
      return res.status(pageResponse.status).json({
        error: `Failed to fetch page: ${pageResponse.statusText}`
      });
    }

    const html = await pageResponse.text();

    // Check for CAPTCHA or login redirect
    if (html.includes('验证码') || html.includes('captcha') ||
        html.includes('/login') || html.includes('请先登录')) {
      return res.status(403).json({
        error: 'Access blocked - Xiaohongshu requires verification. Please try a fresh share link from the app.'
      });
    }

    // Step 4: Extract __INITIAL_STATE__
    console.log('Extracting initial state...');
    const initialState = extractInitialState(html);

    if (!initialState) {
      return res.status(500).json({
        error: 'Could not extract video data from page. The page format may have changed or the content is not available.'
      });
    }

    // Step 5: Extract video info
    console.log('Extracting video info...');
    const videoInfo = extractVideoInfo(initialState, postId);

    if (!videoInfo) {
      return res.status(404).json({
        error: 'No video found. This might be an image post or the video is not available.'
      });
    }

    console.log('Success! Found', videoInfo.streams.length, 'video streams');
    return res.json(videoInfo);

  } catch (error) {
    console.error('Error processing request:', error);
    return res.status(500).json({
      error: `Failed to process video: ${error instanceof Error ? error.message : 'Unknown error'}`
    });
  }
});

// Proxy endpoint for downloading (to avoid CORS on CDN)
app.get('/api/download', async (req, res) => {
  const { url, filename } = req.query;

  if (!url || typeof url !== 'string') {
    return res.status(400).json({ error: 'URL is required' });
  }

  try {
    const response = await fetch(url, {
      headers: {
        ...BROWSER_HEADERS,
        'Referer': 'https://www.xiaohongshu.com/',
      },
    });

    if (!response.ok) {
      return res.status(response.status).json({
        error: `Failed to download: ${response.statusText}`
      });
    }

    // Set headers for download
    const contentType = response.headers.get('content-type') || 'video/mp4';
    const contentLength = response.headers.get('content-length');

    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `attachment; filename="${filename || 'video.mp4'}"`);
    if (contentLength) {
      res.setHeader('Content-Length', contentLength);
    }

    // Stream the response
    const reader = response.body?.getReader();
    if (!reader) {
      return res.status(500).json({ error: 'Failed to read response body' });
    }

    const stream = new ReadableStream({
      async start(controller) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
        controller.close();
      },
    });

    // Convert to Node stream and pipe
    const nodeStream = await streamToNodeReadable(stream);
    nodeStream.pipe(res);

  } catch (error) {
    console.error('Download error:', error);
    return res.status(500).json({
      error: `Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    });
  }
});

// Helper to convert Web Stream to Node Readable
async function streamToNodeReadable(webStream: ReadableStream): Promise<NodeJS.ReadableStream> {
  const { Readable } = await import('stream');
  const reader = webStream.getReader();

  return new Readable({
    async read() {
      const { done, value } = await reader.read();
      if (done) {
        this.push(null);
      } else {
        this.push(Buffer.from(value));
      }
    },
  });
}

// Health check
app.get('/api/health', (_, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

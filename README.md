# RedNote Video Downloader

A simple web app to download videos from RedNote (Xiaohongshu) by pasting a share link.

## Features

- Paste any RedNote share URL (xhslink.com or xiaohongshu.com)
- Extracts video information including title, author, and duration
- Multiple quality options when available (H.264, H.265, AV1)
- Direct MP4 download without watermarks
- Clean, mobile-friendly interface

## How It Works

1. The app accepts RedNote share links from the mobile app
2. It resolves short URLs and extracts the video metadata from the page
3. Parses the `window.__INITIAL_STATE__` JSON to find video stream URLs
4. Provides direct download links for the MP4 files

## Getting Started

### Installation

```bash
npm install
```

### Development

Run both the frontend and backend in development mode:

```bash
npm run dev
```

This starts:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

### Build for Production

```bash
npm run build
```

## Usage

1. Open the RedNote (Xiaohongshu) app on your phone
2. Find a video you want to download
3. Tap the share button and copy the link
4. Paste the link in the app and click "Get Video"
5. Choose your preferred quality and download

## Technical Notes

- Videos are served as MP4 files from Xiaohongshu's CDN
- Share links contain an `xsec_token` that may expire
- Rate limiting applies - avoid bulk downloads
- For personal use only

## Technologies

- React 19
- TypeScript
- Vite
- Express.js (backend)
- Node.js fetch API

## Disclaimer

This tool is for personal use only. Please respect content creators' rights and Xiaohongshu's terms of service.

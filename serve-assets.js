const http = require('http');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname);
const port = Number(process.env.FACE_DUMMY_ASSET_PORT || 4177);

const mimeTypes = {
  '.csv': 'text/csv; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
};

function sendError(res, statusCode, message) {
  res.statusCode = statusCode;
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.end(message);
}

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.statusCode = 204;
    res.end();
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendError(res, 405, 'Method Not Allowed');
    return;
  }

  let requestPath;
  try {
    requestPath = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
  } catch {
    sendError(res, 400, 'Bad Request');
    return;
  }

  const filePath = path.resolve(root, `.${requestPath}`);
  if (filePath !== root && !filePath.startsWith(`${root}${path.sep}`)) {
    sendError(res, 403, 'Forbidden');
    return;
  }

  fs.stat(filePath, (error, stats) => {
    if (error || !stats.isFile()) {
      sendError(res, 404, 'Not Found');
      return;
    }

    res.statusCode = 200;
    res.setHeader('Content-Type', mimeTypes[path.extname(filePath).toLowerCase()] || 'application/octet-stream');
    res.setHeader('Cache-Control', 'no-store');

    if (req.method === 'HEAD') {
      res.end();
      return;
    }

    fs.createReadStream(filePath).on('error', () => {
      if (!res.headersSent) sendError(res, 500, 'Internal Server Error');
      else res.destroy();
    }).pipe(res);
  });
});

server.listen(port, () => {
  console.log(`Face Dummy assets: http://localhost:${port}`);
  console.log('Keep this process running while testing the local Figma plugin.');
});

process.on('SIGINT', () => server.close(() => process.exit(0)));
process.on('SIGTERM', () => server.close(() => process.exit(0)));

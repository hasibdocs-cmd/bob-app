/**
 * CRA dev-server proxy configuration.
 *
 * In Docker Compose the backend container is reachable as "http://backend:8000",
 * NOT "http://localhost:8000" (which would resolve to the frontend container itself).
 *
 * The REACT_APP_PROXY_TARGET env var lets docker-compose.yml inject the right host
 * while keeping plain `npm start` on a developer's machine working unchanged.
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

const target = process.env.REACT_APP_PROXY_TARGET || 'http://localhost:8000';

module.exports = function (app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target,
      changeOrigin: true,
    })
  );
};

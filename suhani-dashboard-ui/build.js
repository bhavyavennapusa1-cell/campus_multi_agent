const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'frontend');
const distDir = path.join(__dirname, 'dist');

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy files from frontend to dist
const files = fs.readdirSync(srcDir);
files.forEach(file => {
  if (file === '__pycache__') return;
  const srcFile = path.join(srcDir, file);
  const distFile = path.join(distDir, file);
  if (fs.statSync(srcFile).isFile()) {
    fs.copyFileSync(srcFile, distFile);
  }
});

// Copy files inside suhani-dashboard-ui if any
const localFiles = fs.readdirSync(__dirname);
localFiles.forEach(file => {
  if (['node_modules', 'dist', 'package.json', 'build.js'].includes(file)) return;
  const srcFile = path.join(__dirname, file);
  const distFile = path.join(distDir, file);
  if (fs.statSync(srcFile).isFile()) {
    fs.copyFileSync(srcFile, distFile);
  }
});

console.log('Build completed successfully. dist/ contains index.html and static assets.');

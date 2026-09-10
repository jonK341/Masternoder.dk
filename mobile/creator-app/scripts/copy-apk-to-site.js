/** Copy release APK to site static/downloads for self-hosted distribution. */
const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, '..', 'android', 'app', 'build', 'outputs', 'apk', 'release', 'app-release.apk');
const destDir = path.join(__dirname, '..', '..', '..', 'static', 'downloads');
const dest = path.join(destDir, 'masternoder-creator.apk');

if (!fs.existsSync(src)) {
  console.error('Release APK not found. Run npm run build:android first.');
  process.exit(1);
}
fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(src, dest);
console.log('Published:', dest, '(' + fs.statSync(dest).size + ' bytes)');

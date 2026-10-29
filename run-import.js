const path = require('path');
const { spawnSync } = require('child_process');

const localPython = path.resolve(__dirname, '../../face-image-normalizer/.venv/bin/python');
const python = require('fs').existsSync(localPython) ? localPython : 'python3';
const script = path.join(__dirname, 'import_3d_assets.py');
const result = spawnSync(python, [script, ...process.argv.slice(2)], { stdio: 'inherit' });

if (result.error) {
  console.error(`Could not start Python importer: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);

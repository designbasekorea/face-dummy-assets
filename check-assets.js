const fs = require('fs');
const path = require('path');

const repoDir = __dirname;
const imageDir = path.join(repoDir, 'img');
const proDir = path.join(imageDir, 'pro');
const metadataPath = path.join(repoDir, 'imageMetadata2.csv');

function parseCsvLine(line) {
  return line.split(',').map(value => value.trim());
}

const lines = fs.readFileSync(metadataPath, 'utf8').trim().split(/\r?\n/);
const [header, ...rows] = lines;
const fields = parseCsvLine(header);
const metadata = rows.map(parseCsvLine).map(values => Object.fromEntries(fields.map((field, index) => [field, values[index] || ''])));
const metadataNames = new Set(metadata.map(row => row.filename));
const baseNames = new Set(fs.readdirSync(imageDir).filter(file => /\.(jpg|jpeg|png|svg)$/i.test(file)));
const proNames = new Set(fs.readdirSync(proDir).filter(file => /\.(jpg|jpeg|png|svg)$/i.test(file)));

const missingBase = metadata.filter(row => !fs.existsSync(path.join(imageDir, row.filename))).map(row => row.filename);
const missingPro = metadata.filter(row => !fs.existsSync(path.join(proDir, row.filename))).map(row => row.filename);
const metadataMissing = [...baseNames].filter(filename => !metadataNames.has(filename));
const extraPro = [...proNames].filter(filename => !baseNames.has(filename));
const duplicateMetadata = metadata.map(row => row.filename).filter((filename, index, values) => values.indexOf(filename) !== index);
const invalidAddedAt = metadata.filter(row => row.addedAt && !Number.isFinite(Date.parse(row.addedAt))).map(row => row.filename);

if (missingBase.length || missingPro.length || metadataMissing.length || extraPro.length || duplicateMetadata.length || invalidAddedAt.length) {
  console.error(JSON.stringify({ missingBase, missingPro, metadataMissing, extraPro, duplicateMetadata, invalidAddedAt }, null, 2));
  process.exit(1);
}

console.log(`Assets OK: ${baseNames.size} preview images, ${proNames.size} paid images, ${metadata.length} metadata rows.`);

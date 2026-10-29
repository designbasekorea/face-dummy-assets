const fs = require('fs');
const path = require('path');

const assetsDir = path.join(__dirname, 'img');
const outputFilePath = path.join(assetsDir, 'imageList.json');

const naturalKey = value => value.split(/(\d+)/).map(part => (/^\d+$/.test(part) ? Number(part) : part.toLowerCase()));

const imageList = fs.readdirSync(assetsDir)
    .filter(file => /\.(jpg|jpeg|png|svg)$/i.test(file))
    .sort((a, b) => {
        const left = naturalKey(a);
        const right = naturalKey(b);
        for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
            if (left[index] === right[index]) continue;
            return left[index] < right[index] ? -1 : 1;
        }
        return 0;
    })
    .map(file => `https://cdn.jsdelivr.net/gh/designbasekorea/face-dummy-assets@main/img/${file}`);

// JSON 파일로 결과 저장
fs.writeFileSync(outputFilePath, JSON.stringify(imageList, null, 2));
console.log('Image list JSON file generated.');

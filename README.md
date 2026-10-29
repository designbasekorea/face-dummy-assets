# Face Dummy — 공식 플러그인 에셋

Designbase가 관리하는 **Face Dummy Figma 플러그인 전용 이미지 에셋 저장소**입니다.
무료 미리보기, 고해상도 원본, 이미지 목록을 플러그인과 CDN에 제공합니다.

## 저작권 및 이용 조건

Copyright © 2026 Designbase. All rights reserved, to the extent applicable.
이미지와 저장소 구성에 관한 권리는 Designbase 또는 각 권리자에게 있습니다.
AI로 생성하거나 보정한 이미지가 포함되어 있으며, 이 표기는 개별 AI 생성물에
독점적 저작권이 성립한다는 보증을 뜻하지 않습니다.

- 이 저장소는 플러그인 배포를 위해 공개되어 있으며, 오픈소스·퍼블릭 도메인 에셋 팩이 아닙니다.
- Face Dummy에서 정당하게 제공받은 이미지는 해당 플러그인의 이용 조건과 구매 권한에 따라 디자인·목업·프로토타입 등 최종 결과물에 사용할 수 있습니다.
- 공개 URL에 접근할 수 있다는 사실만으로 유료 플러그인 기능 또는 원본 재배포 권한이 부여되지는 않습니다.
- 별도 허락 없이 원본·변형 에셋을 묶어 재배포·재판매하거나, 에셋 팩·경쟁 플러그인·이미지 API로 제공할 수 없습니다.
- 별도 권리 표시가 있는 자료에는 해당 조건이 우선합니다.

자세한 조건은 [LICENSE](LICENSE)를 확인하세요. 문의: https://designbase.co.kr

## 공식 배포 주소

- 저장소: https://github.com/designbasekorea/face-dummy-assets
- 메타데이터: https://cdn.jsdelivr.net/gh/designbasekorea/face-dummy-assets@main/imageMetadata2.csv
- 미리보기: `img/*.png`
- 고해상도 원본: `img/pro/*.png`

현재 326개 이미지의 미리보기·고해상도 쌍을 제공합니다.
공개 저장소이므로 파일 URL은 열람 가능합니다. 플러그인의 유료 기능 접근은 라이선스로 관리합니다.

## 에셋 관리 방법

The plugin reads this repository through jsDelivr:

- metadata: `imageMetadata2.csv`
- free previews: `img/*.png` (style-specific dimensions)
- paid images: `img/pro/*.png` (style-specific dimensions)

## Add a new image style

For the 3D Avatar style, use the square pipeline so every newly generated asset has the same 1:1 ratio:

```bash
mkdir -p incoming/3d-avatar
# Put new square or transparent avatar PNGs in incoming/3d-avatar
npm run assets:import:avatar
```

This creates `100×100` free previews and `600×600` paid assets without cropping, using the `graphic-3d-avatar-square-*` namespace. The plugin treats these as square assets, while the earlier imported avatar batch remains available with its original 3:4 dimensions.

For newly generated realistic portraits, first place cleaned, transparent square PNGs in `incoming/realistic` and run:

```bash
mkdir -p incoming/realistic
# Put 1:1 transparent realistic portrait PNGs in incoming/realistic
npm run assets:import:realistic
```

This uses the `Realistic / International Adult` metadata type, infers gender from `female` or `male` in each filename, and creates the same `100×100` / `600×600` square pair under the `realistic-international-adult-*` namespace.

For other image styles, or when preserving a source style's native dimensions is intentional, use the generic importer:

```bash
npm run assets:import -- --source-dir "/path/to/source-images"
```

The importer assigns stable names, creates preview and paid variants without cropping, updates the metadata CSV, regenerates `img/imageList.json`, and remembers source hashes so rerunning the same batch does not duplicate it.

Imported images are marked as paid by default. Use `--paid ""` if a batch should be free.

New imports automatically record an ISO UTC `addedAt` timestamp in `imageMetadata2.csv` and the import manifest. The plugin shows NEW for seven days from that timestamp. If publication is delayed, set `addedAt` to the actual release time when publishing. Reimporting an existing image preserves its date and does not make it new again. Existing images with no reliable date leave this field blank and never show NEW.

NEW appears on style chips, section headings, and new thumbnails. Successfully loaded thumbnails that enter the visible viewport are remembered in Figma clientStorage. Their badge stays visible during that visit and disappears the next time the plugin opens. Images the user has not scrolled to remain new until viewed or the seven-day period expires. History is per plugin on the current Figma installation; the development plugin and published plugin have separate histories.

If a filename does not clearly say male/female, the importer leaves the gender blank and writes `asset-import-review.csv` for manual review. After reviewing it, copy the final gender values into `imageMetadata2.csv`.

Before publishing, run:

```bash
npm run assets:check
```

To preview the current assets locally from the Figma plugin before pushing to GitHub, run:

```bash
npm run assets:serve
```

This serves the repository at `http://localhost:4177` with CORS enabled for the Figma UI iframe. Keep it running while using the plugin's `npm run build:local` development build.

Then review the diff and push this repository. The plugin will pick up the new CSV and images through jsDelivr after GitHub/CDN propagation.

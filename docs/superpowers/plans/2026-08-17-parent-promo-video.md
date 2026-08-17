# Parent Promo Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and render a 15-second, 9:16 Remotion advertisement for Shanghai junior-middle-school parents using the website's real brand and interface.

**Architecture:** Add an isolated `promo-video` Remotion project beside the existing application. A deterministic local asset pipeline captures privacy-safe website screens and creates original audio; focused React scene components assemble those assets into a 450-frame composition, and validation scripts inspect timing, keyframes, dimensions, pixels, and audio/video streams.

**Tech Stack:** Remotion 4.0.506, React 19, TypeScript, Playwright, Sharp, macOS `say`, FFmpeg/ffprobe, Node.js test runner.

## Global Constraints

- Composition ID is `ParentPromo`, 1080 x 1920, 30 fps, exactly 450 frames.
- The output is H.264 MP4 with a warm adult female Mandarin voiceover and quiet original background music.
- Use `web/logo.png`, the existing Noto Sans SC fonts, and current website interface imagery.
- All screenshots use synthetic demo content; no real student name, exam, family access code, or history record may appear.
- Keep core text at least 72 px from left/right and 140 px from top/bottom.
- Main headlines are at least 84 px and important supporting text is at least 44 px.
- Animations use `useCurrentFrame()`, `interpolate()`, and Remotion timing APIs only; no CSS transitions or keyframe animations.
- Final output path is `promo-video/out/parent-promo-15s.mp4`.

---

### Task 1: Remotion Project and Timing Contract

**Files:**
- Create: `promo-video/package.json`
- Create: `promo-video/tsconfig.json`
- Create: `promo-video/remotion.config.ts`
- Create: `promo-video/src/index.ts`
- Create: `promo-video/src/Root.tsx`
- Create: `promo-video/src/timing.mjs`
- Create: `promo-video/test/timing.test.mjs`
- Create: `promo-video/.gitignore`

**Interfaces:**
- Produces: `FPS`, `WIDTH`, `HEIGHT`, `DURATION_IN_FRAMES`, and `SCENES` from `src/timing.mjs`.
- Produces: registered composition ID `ParentPromo` for later scene rendering.

- [ ] **Step 1: Write the failing timing test**

```js
import assert from 'node:assert/strict';
import test from 'node:test';
import {DURATION_IN_FRAMES, FPS, HEIGHT, SCENES, WIDTH} from '../src/timing.mjs';

test('parent promo is an exact 15-second vertical composition', () => {
  assert.equal(FPS, 30);
  assert.equal(WIDTH, 1080);
  assert.equal(HEIGHT, 1920);
  assert.equal(DURATION_IN_FRAMES, 450);
  assert.equal(DURATION_IN_FRAMES / FPS, 15);
});

test('scene windows cover every frame exactly once', () => {
  assert.deepEqual(SCENES, [
    {id: 'problem', from: 0, duration: 90},
    {id: 'analysis', from: 90, duration: 120},
    {id: 'worksheet', from: 210, duration: 120},
    {id: 'closing', from: 330, duration: 120},
  ]);
  assert.equal(SCENES.at(-1).from + SCENES.at(-1).duration, DURATION_IN_FRAMES);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd promo-video && node --test test/timing.test.mjs`

Expected: FAIL because `src/timing.mjs` does not exist.

- [ ] **Step 3: Add the minimal project and timing implementation**

Pin compatible dependencies in `package.json`:

```json
{
  "scripts": {
    "test": "node --test test/*.test.mjs",
    "studio": "remotion studio --no-open",
    "render": "remotion render src/index.ts ParentPromo out/parent-promo-15s.mp4 --codec=h264 --crf=18"
  },
  "dependencies": {
    "@remotion/cli": "4.0.506",
    "@remotion/fonts": "4.0.506",
    "@remotion/media": "4.0.506",
    "@remotion/transitions": "4.0.506",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "remotion": "4.0.506",
    "sharp": "0.34.5"
  },
  "devDependencies": {
    "@types/react": "19.2.14",
    "@types/node": "24.10.13",
    "typescript": "5.9.3"
  }
}
```

Implement `timing.mjs` with the exact values asserted above. Register `ParentPromo` in `Root.tsx` using those constants and a temporary white `AbsoluteFill` component.

- [ ] **Step 4: Install dependencies and verify GREEN**

Run: `cd promo-video && npm install`

Run: `cd promo-video && npm test`

Expected: two passing timing tests.

- [ ] **Step 5: Commit the project contract**

```bash
git add promo-video/package.json promo-video/package-lock.json promo-video/tsconfig.json promo-video/remotion.config.ts promo-video/src/index.ts promo-video/src/Root.tsx promo-video/src/timing.mjs promo-video/test/timing.test.mjs promo-video/.gitignore
git commit -m "feat: scaffold parent promo video"
```

### Task 2: Privacy-Safe Brand, Screenshot, and Audio Assets

**Files:**
- Create: `promo-video/scripts/prepare-assets.mjs`
- Create: `promo-video/scripts/capture-site.mjs`
- Create: `promo-video/scripts/generate-music.mjs`
- Create: `promo-video/scripts/generate-voiceover.sh`
- Create: `promo-video/test/assets.test.mjs`
- Create: `promo-video/public/logo.png`
- Create: `promo-video/public/fonts/NotoSansSC-Regular.ttf`
- Create: `promo-video/public/fonts/NotoSansSC-Bold.ttf`
- Create: `promo-video/public/screens/problem.png`
- Create: `promo-video/public/screens/analysis.png`
- Create: `promo-video/public/screens/worksheet.png`
- Create: `promo-video/public/screens/wrong-bank.png`
- Create: `promo-video/public/audio/music.wav`
- Create: `promo-video/public/audio/voice-problem.wav`
- Create: `promo-video/public/audio/voice-analysis.wav`
- Create: `promo-video/public/audio/voice-worksheet.wav`
- Create: `promo-video/public/audio/voice-closing.wav`

**Interfaces:**
- Consumes: `web/logo.png`, `fonts/NotoSansSC-Regular.ttf`, `fonts/NotoSansSC-Bold.ttf`, and the local/production website.
- Produces: stable static assets referenced through `staticFile()` by Task 3.

- [ ] **Step 1: Write the failing asset test**

Use `sharp` to assert each PNG is at least 900 px wide and 1200 px tall. Use `fs.stat()` to assert the logo, fonts, music, and four voice clips are non-empty. Read PNG metadata and fail if any required asset is missing.

```js
for (const name of ['problem', 'analysis', 'worksheet', 'wrong-bank']) {
  const metadata = await sharp(`public/screens/${name}.png`).metadata();
  assert.ok(metadata.width >= 900);
  assert.ok(metadata.height >= 1200);
}
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd promo-video && npm test`

Expected: FAIL with a missing `public/screens/problem.png` or equivalent missing asset.

- [ ] **Step 3: Implement the asset preparation scripts**

`prepare-assets.mjs` copies the existing logo and both fonts. `capture-site.mjs` launches local Chrome with Playwright, loads the current website, and creates four 1080 x 1500 screenshots. It may inject only these synthetic values into its temporary page:

```js
const demo = {
  studentName: '小宇',
  subject: '数学',
  wrongCount: 6,
  weakPoints: ['一元一次方程', '相交线与平行线'],
  reviewDay: '第 1 天',
};
```

`generate-music.mjs` writes a deterministic 15-second, 48 kHz stereo WAV with low-volume C-major/A-minor/F-major/G-major pads and soft chimes at scene boundaries. `generate-voiceover.sh` uses macOS `say -v Tingting` and FFmpeg to create one WAV per exact line:

```text
孩子错题不少，却不知道该从哪里补？
上传试卷，AI 自动定位错因和薄弱知识点。
按上海教材生成针对性复习卷，题目答案分开。
每次错误都有记录，每次复习都有方向。虾胡闹，有钳途。
```

- [ ] **Step 4: Generate assets and verify GREEN**

Run: `cd promo-video && node scripts/prepare-assets.mjs`

Run: `cd promo-video && node scripts/capture-site.mjs`

Run: `cd promo-video && node scripts/generate-music.mjs`

Run: `cd promo-video && bash scripts/generate-voiceover.sh`

Run: `cd promo-video && npm test`

Expected: timing and asset tests pass; all screenshots contain only synthetic demo information.

- [ ] **Step 5: Commit deterministic assets and scripts**

```bash
git add promo-video/scripts promo-video/test/assets.test.mjs promo-video/public
git commit -m "feat: prepare promo media assets"
```

### Task 3: Four-Scene Remotion Composition

**Files:**
- Create: `promo-video/src/ParentPromo.tsx`
- Create: `promo-video/src/theme.ts`
- Create: `promo-video/src/fonts.ts`
- Create: `promo-video/src/components/Caption.tsx`
- Create: `promo-video/src/components/PhoneFrame.tsx`
- Create: `promo-video/src/components/BrandMark.tsx`
- Create: `promo-video/src/scenes/ProblemScene.tsx`
- Create: `promo-video/src/scenes/AnalysisScene.tsx`
- Create: `promo-video/src/scenes/WorksheetScene.tsx`
- Create: `promo-video/src/scenes/ClosingScene.tsx`
- Modify: `promo-video/src/Root.tsx`
- Create: `promo-video/test/source-contract.test.mjs`

**Interfaces:**
- Consumes: `SCENES` from `timing.mjs` and all `public/` assets from Task 2.
- Produces: a renderable `ParentPromo` component with four readable scenes and synchronized audio.

- [ ] **Step 1: Write the failing source contract**

Read the scene source files and assert that all approved captions and all required static asset paths are present. Assert that `ParentPromo.tsx` imports `Audio` from `@remotion/media`, uses four `Sequence` blocks, and references the four scene components.

```js
assert.match(parentPromo, /@remotion\/media/);
assert.match(problemScene, /错题不少，却不知道从哪里补/);
assert.match(analysisScene, /上传试卷/);
assert.match(worksheetScene, /按上海教材/);
assert.match(closingScene, /每次错误都有记录/);
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd promo-video && npm test`

Expected: FAIL because the scene files do not exist.

- [ ] **Step 3: Implement shared components and scenes**

Load both local font weights with `@remotion/fonts`. Use `CanvasImage` or `Img` with `staticFile()` for images. Each scene must have one primary headline, one interface focal point, and motion driven only by `useCurrentFrame()` plus clamped `interpolate()` calls.

Use these frame windows from the global composition:

```text
ProblemScene:   0-89
AnalysisScene:  90-209
WorksheetScene: 210-329
ClosingScene:   330-449
```

The closing scene keeps the full Logo, `虾胡闹，有钳途`, and `上传试卷，开始针对性复习` fully visible from frame 396 through frame 449. Add the music bed at volume 0.12. Add voice clips in their matching `Sequence` blocks at volume 1.0.

- [ ] **Step 4: Verify the source contract and typecheck**

Run: `cd promo-video && npm test`

Run: `cd promo-video && npx tsc --noEmit`

Expected: all tests pass and TypeScript reports no errors.

- [ ] **Step 5: Commit the composition**

```bash
git add promo-video/src promo-video/test/source-contract.test.mjs
git commit -m "feat: compose parent promo scenes"
```

### Task 4: Keyframe and Final Video Validation

**Files:**
- Create: `promo-video/scripts/render-keyframes.mjs`
- Create: `promo-video/scripts/validate-render.mjs`
- Create: `promo-video/test/rendered-frames.test.mjs`
- Create: `promo-video/out/keyframes/problem.png`
- Create: `promo-video/out/keyframes/analysis.png`
- Create: `promo-video/out/keyframes/worksheet.png`
- Create: `promo-video/out/keyframes/closing.png`
- Create: `promo-video/out/parent-promo-15s.mp4`

**Interfaces:**
- Consumes: composition ID `ParentPromo` and all assets/components from Tasks 1-3.
- Produces: validated MP4 at `promo-video/out/parent-promo-15s.mp4`.

- [ ] **Step 1: Write the failing rendered-frame test**

Use Sharp to assert frames 45, 150, 270, and 420 are 1080 x 1920, have at least 5,000 distinct sampled RGB values, and are not predominantly transparent, pure white, or pure black. Check the closing frame contains non-background pixels in both the Logo zone and CTA zone.

- [ ] **Step 2: Run the rendered-frame test and verify RED**

Run: `cd promo-video && node --test test/rendered-frames.test.mjs`

Expected: FAIL because `out/keyframes/problem.png` does not exist.

- [ ] **Step 3: Render and inspect keyframes**

`render-keyframes.mjs` invokes Remotion Still for frames 45, 150, 270, and 420. Run it, then inspect all four images visually. Revise only scene layout, timing, or text sizes required to eliminate clipping, overlap, unreadable text, blank areas, or incorrect assets.

Run: `cd promo-video && node scripts/render-keyframes.mjs`

Run: `cd promo-video && node --test test/rendered-frames.test.mjs`

Expected: keyframe tests pass and all four frames look intentional at phone size.

- [ ] **Step 4: Render and validate the final MP4**

Run: `cd promo-video && npm run render`

`validate-render.mjs` invokes ffprobe and asserts:

```text
duration: 15.000 seconds within +/- 0.05
video codec: h264
width x height: 1080 x 1920
frame rate: 30/1
audio stream: present
file size: greater than 1 MB
```

Run: `cd promo-video && node scripts/validate-render.mjs out/parent-promo-15s.mp4`

Expected: every assertion passes.

- [ ] **Step 5: Run final repository checks and commit validation tooling**

Run: `cd promo-video && npm test`

Run: `.venv/bin/python -m unittest discover -s tests`

Run: `git diff --check`

```bash
git add promo-video/scripts/render-keyframes.mjs promo-video/scripts/validate-render.mjs promo-video/test/rendered-frames.test.mjs
git commit -m "test: verify parent promo render"
```

Keep `promo-video/out/` ignored by Git while leaving the rendered MP4 on disk for the user.


// Playwright の最小スモークテスト（開始用）。実際の製品の主要フローに合わせて書き換えて使う。
// 前提: `npm i -D @playwright/test` と `npx playwright install chromium`、playwright.config で baseURL を指定。
import { test, expect } from '@playwright/test';

test('トップページが応答し、主要な内容が表示される', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto('/');
  expect(response?.ok(), 'トップページが成功応答を返す').toBeTruthy();
  await expect(page.locator('body')).toBeVisible();
  expect(errors, '捕捉されなかったページエラー').toEqual([]);
});

// 製品の最も重要な操作フロー（例: 入力 → 送信 → 結果の表示、エラー時の表示）を test() として足す。
// トップページのスモークテストだけでは、主要フローのE2Eとは認めない。

import { test, expect } from '@playwright/test';

// CTA сущностной страницы ведёт на ту же запись в компендиуме Table (#164).

const UTM = 'utm_source=rules&utm_medium=cta&utm_campaign=funnel&utm_content=';

test('заклинание и состояние SRD 5.2 — deep-link в компендиум с utm', async ({ page }) => {
  for (const [url, target] of [
    ['/ru/dnd/srd-5.2/spells/fireball/', 'https://omnisgm.com/compendium/dnd2024/spell/fireball?'],
    ['/en/dnd/srd-5.2/rules-glossary/conditions/blinded/', 'https://omnisgm.com/compendium/dnd2024/rule/condition-blinded?'],
    ['/en/dnd/srd-5.2/rules-glossary/term/unarmed-strike/', 'https://omnisgm.com/compendium/dnd2024/action/unarmed-strike?'],
  ]) {
    await page.goto(url);
    const cta = page.locator('a.rd-cta');
    await expect(cta, url).toHaveAttribute('data-cta', 'compendium');
    const href = await cta.getAttribute('href');
    expect(href?.startsWith(target), `${url} → ${href}`).toBe(true);
    expect(href, url).toContain(UTM);
  }
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  await expect(page.locator('a.rd-cta .rd-cta-title')).toHaveText('Открыть в OmnisGM');
});

test('существо, SRD 5.1, Daggerheart и хаб — общий CTA воронки', async ({ page }) => {
  for (const url of [
    '/en/dnd/srd-5.2/monsters-a-z/aboleth/',
    '/ru/dnd/srd-5.1/spells/fireball/',
    '/ru/daggerheart/srd-1.0/ancestries/dwarf/',
    '/en/dnd/srd-5.2/spells/all/',
  ]) {
    await page.goto(url);
    const cta = page.locator('a.rd-cta');
    await expect(cta, url).toHaveAttribute('data-cta', 'funnel');
    expect(await cta.getAttribute('href'), url).toMatch(/^https:\/\/omnisgm\.com\/(ru)?\?utm_source=rules/);
  }
});

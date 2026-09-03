import assert from "node:assert/strict";
import test from "node:test";
import { CATALOGS, resolveLanguage, SUPPORTED_LANGUAGES, translate } from "./i18n-catalog.ts";

test("every supported language implements the complete catalog", () => {
  const expectedKeys = Object.keys(CATALOGS.en).sort();
  for (const { code } of SUPPORTED_LANGUAGES) {
    assert.deepEqual(Object.keys(CATALOGS[code]).sort(), expectedKeys);
    for (const key of expectedKeys) {
      const messageKey = key as keyof typeof CATALOGS.en;
      const placeholderNames = (text: string) => [...text.matchAll(/\{([^}]+)\}/g)].map((match) => match[1]).sort();
      assert.ok(CATALOGS[code][messageKey].trim());
      assert.deepEqual(placeholderNames(CATALOGS[code][messageKey]), placeholderNames(CATALOGS.en[messageKey]), `${code}.${key}`);
    }
  }
});

test("translations interpolate values and resolve browser locales", () => {
  assert.equal(translate("en", "ocr.summary", { count: 6 }), "6 text regions detected");
  assert.equal(translate("zh-CN", "preview.position", { x: 20, y: 35 }), "位置 20, 35");
  assert.equal(resolveLanguage("de-DE"), "de");
  assert.equal(resolveLanguage("es-ES"), "en");
});

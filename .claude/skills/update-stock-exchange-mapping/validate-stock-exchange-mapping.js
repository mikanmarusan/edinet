#!/usr/bin/env node
/**
 * config/stock_exchange_mapping.yml のバリデーションスクリプト
 *
 * Usage: node validate-stock-exchange-mapping.js <path-to-stock_exchange_mapping.yml>
 *
 * 検証項目:
 * - YAML構文（このファイル専用の軽量パーサー）
 * - 証券コード形式（4桁: 数字 or 数字+英字）
 * - 取引所コード（N, F, S のみ）
 * - 重複コードの検出
 * - セクションコメントの存在
 * - 各セクション内のソート順
 * - 各取引所の件数レポート
 */

const fs = require('fs');

const VALID_EXCHANGES = new Set(['N', 'F', 'S']);
const CODE_PATTERN = /^\d{3,4}[A-Z0-9]?$/;
const ENTRY_PATTERN = /^\s+"([^"]+)":\s+"([^"]+)"$/;
const EXPECTED_SECTIONS = ['# 名古屋証券取引所 (N)', '# 福岡証券取引所 (F)', '# 札幌証券取引所 (S)'];

function validate(yamlPath) {
  let content;
  try {
    content = fs.readFileSync(yamlPath, 'utf-8');
  } catch (e) {
    console.error(`ERROR: Cannot read ${yamlPath}: ${e.message}`);
    process.exit(1);
  }

  const lines = content.split('\n');
  const errors = [];
  const entries = new Map();
  const counts = { N: 0, F: 0, S: 0 };

  if (!lines[0] || lines[0].trim() !== 'stock_exchanges:') {
    errors.push(`Line 1: Expected 'stock_exchanges:' root key, got '${lines[0]}'`);
  }

  for (const section of EXPECTED_SECTIONS) {
    if (!content.includes(section)) {
      errors.push(`Missing section comment: '${section}'`);
    }
  }

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    if (line.trim() === '' || line.trim().startsWith('#')) continue;

    const match = line.match(ENTRY_PATTERN);
    if (!match) {
      if (line.trim() !== '') {
        errors.push(`Line ${lineNum}: Invalid format: '${line.trim()}'`);
      }
      continue;
    }

    const code = match[1];
    const exchange = match[2];

    if (!CODE_PATTERN.test(code)) {
      errors.push(`Line ${lineNum}: Invalid code format: '${code}'`);
    }

    if (!VALID_EXCHANGES.has(exchange)) {
      errors.push(`Line ${lineNum}: Invalid exchange code: '${exchange}'`);
    }

    if (entries.has(code)) {
      const prev = entries.get(code);
      errors.push(`Line ${lineNum}: Duplicate code '${code}' (first at line ${prev.line})`);
    } else {
      entries.set(code, { exchange, line: lineNum });
      if (counts[exchange] !== undefined) {
        counts[exchange]++;
      }
    }
  }

  const sectionCodes = { N: [], F: [], S: [] };
  for (const [code, { exchange }] of entries) {
    if (sectionCodes[exchange]) {
      sectionCodes[exchange].push(code);
    }
  }
  for (const [ex, codes] of Object.entries(sectionCodes)) {
    const sorted = [...codes].sort();
    for (let i = 0; i < codes.length; i++) {
      if (codes[i] !== sorted[i]) {
        errors.push(`Exchange ${ex}: Codes not sorted. '${codes[i]}' should be at position of '${sorted[i]}'`);
        break;
      }
    }
  }

  const total = counts.N + counts.F + counts.S;
  console.log(`Stock Exchange Mapping Validation`);
  console.log(`=================================`);
  console.log(`File: ${yamlPath}`);
  console.log(`Total: ${total} codes`);
  console.log(`  N (Nagoya):  ${counts.N}`);
  console.log(`  F (Fukuoka): ${counts.F}`);
  console.log(`  S (Sapporo): ${counts.S}`);

  if (errors.length > 0) {
    console.log(`\nErrors (${errors.length}):`);
    for (const err of errors) {
      console.log(`  - ${err}`);
    }
    process.exit(1);
  } else {
    console.log(`\nValidation passed!`);
    process.exit(0);
  }
}

const yamlPath = process.argv[2];
if (!yamlPath) {
  console.error('Usage: node validate-stock-exchange-mapping.js <path-to-stock_exchange_mapping.yml>');
  process.exit(1);
}
validate(yamlPath);

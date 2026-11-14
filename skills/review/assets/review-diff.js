(function (root) {
  "use strict";

  function pairLines(lines) {
    const rows = [];
    let old = [];
    let added = [];
    const flush = () => {
      for (let i = 0; i < Math.max(old.length, added.length); i++) {
        rows.push({old: old[i] ?? null, new: added[i] ?? null});
      }
      old = [];
      added = [];
    };
    lines.forEach((line, index) => {
      if (line.type === "remove") {
        if (added.length) flush();
        old.push(index);
      } else if (line.type === "add") {
        added.push(index);
      } else {
        flush();
        rows.push(line.type === "context" ? {old: index, new: index} : {meta: index});
      }
    });
    flush();
    return rows;
  }

  function rangeFor(lines, side, from, to) {
    if (!['old', 'new'].includes(side) || !Number.isInteger(from) || !Number.isInteger(to)) return null;
    const first = Math.min(from, to);
    const last = Math.max(from, to);
    if (first < 0 || last >= lines.length) return null;
    const numbers = lines.slice(first, last + 1).map(line => line[side + '_line']).filter(number => number != null);
    if (!numbers.length || numbers.some((number, i) => i > 0 && number !== numbers[i - 1] + 1)) return null;
    return {start_line: numbers[0], end_line: numbers[numbers.length - 1]};
  }

  function wordRanges(before, after) {
    if (before === after) return {old: [], new: []};
    const tokens = text => Array.from(text.matchAll(/[\p{L}\p{N}_]+|\s+|[^\s]/gu));
    const old = tokens(before);
    const added = tokens(after);
    const width = added.length + 1;
    const maxComparisonCells = 65536;
    if ((old.length + 1) * width > maxComparisonCells) return null;
    const lengths = new Uint16Array((old.length + 1) * width);
    for (let i = old.length - 1; i >= 0; i--) {
      for (let j = added.length - 1; j >= 0; j--) {
        lengths[i * width + j] = old[i][0] === added[j][0]
          ? 1 + lengths[(i + 1) * width + j + 1]
          : Math.max(lengths[(i + 1) * width + j], lengths[i * width + j + 1]);
      }
    }
    const ranges = {old: [], new: []};
    const append = (side, token) => {
      const list = ranges[side];
      const end = token.index + token[0].length;
      if (list.length && list[list.length - 1][1] === token.index) list[list.length - 1][1] = end;
      else list.push([token.index, end]);
    };
    let i = 0;
    let j = 0;
    while (i < old.length || j < added.length) {
      if (i < old.length && j < added.length && old[i][0] === added[j][0]) { i++; j++; }
      else if (i < old.length && (j === added.length || lengths[(i + 1) * width + j] >= lengths[i * width + j + 1])) {
        append('old', old[i++]);
      } else append('new', added[j++]);
    }
    return ranges;
  }

  function moveSelection(lines, selection, key, extend = false) {
    if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) return null;
    const exists = (index, side) => Number.isInteger(index) && index >= 0 && index < lines.length &&
      ['context', 'remove', 'add'].includes(lines[index].type) && lines[index][side + '_line'] != null;
    if (!selection) {
      const preferred = key === 'ArrowLeft' ? 'old' : 'new';
      const index = lines.findIndex((_, i) => exists(i, preferred) || exists(i, preferred === 'old' ? 'new' : 'old'));
      if (index < 0) return null;
      const side = exists(index, preferred) ? preferred : preferred === 'old' ? 'new' : 'old';
      return {side, from: index, to: index};
    }
    const {side, from, to} = selection;
    if (!['old', 'new'].includes(side) || !exists(from, side) || !exists(to, side)) return null;
    if (key === 'ArrowLeft' || key === 'ArrowRight') {
      const nextSide = key === 'ArrowLeft' ? 'old' : 'new';
      if (nextSide === side) return null;
      const pair = pairLines(lines).find(row => row[side] === to);
      const next = pair ? pair[nextSide] : null;
      return next != null && exists(next, nextSide) ? {side: nextSide, from: next, to: next} : null;
    }
    const step = key === 'ArrowDown' ? 1 : -1;
    for (let index = to + step; index >= 0 && index < lines.length; index += step) {
      if (!exists(index, side)) continue;
      if (extend && !rangeFor(lines, side, from, index)) return null;
      return {side, from: extend ? from : index, to: index};
    }
    return null;
  }

  const api = {pairLines, rangeFor, wordRanges, moveSelection};
  root.ReviewDiff = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);

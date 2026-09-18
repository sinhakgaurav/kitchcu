import type { Ingredient, RecipeLine } from "./api";

export type MapperRecipeLine = RecipeLine & {
  source_name?: string;
};

export function normalizeIngredientName(raw: string): string {
  return (raw || "")
    .toLowerCase()
    .replace(/&amp;/g, "and")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function singularize(token: string): string {
  if (token.endsWith("ies") && token.length > 4) return `${token.slice(0, -3)}y`;
  if (token.endsWith("oes") && token.length > 4) return token.slice(0, -2);
  if (token.endsWith("s") && !token.endsWith("ss") && token.length > 3) return token.slice(0, -1);
  return token;
}

function nameVariants(raw: string): string[] {
  const n = normalizeIngredientName(raw);
  if (!n) return [];
  const words = n.split(" ");
  const stemmed = words.map(singularize).join(" ");
  return stemmed !== n ? [n, stemmed] : [n];
}

export function namesMatch(a: string, b: string): boolean {
  const left = nameVariants(a);
  const right = new Set(nameVariants(b));
  return left.some((v) => right.has(v));
}

export function stripIngredientHtml(raw: string): string {
  return raw
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|li|div|h[1-6]|ul|ol)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseDishIngredientTokens(raw: string | null | undefined): string[] {
  const text = stripIngredientHtml(raw ?? "");
  if (!text) return [];
  const seen = new Set<string>();
  const tokens: string[] = [];
  for (const part of text.split(/[,;•·\n|/]+/)) {
    const token = part.replace(/\s+/g, " ").trim().replace(/[.]+$/, "");
    if (token.length < 2) continue;
    const key = normalizeIngredientName(token);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    tokens.push(token);
  }
  return tokens;
}

export function matchPantryIngredient(
  token: string,
  pantry: Ingredient[],
): Ingredient | undefined {
  const variants = nameVariants(token);
  if (!variants.length) return undefined;

  const exact = pantry.find((ing) => namesMatch(ing.name, token));
  if (exact) return exact;

  const scored = pantry
    .map((ing) => {
      const pantryNames = nameVariants(ing.name);
      let score = 0;
      for (const v of variants) {
        for (const p of pantryNames) {
          if (v === p) score = Math.max(score, 100);
          else if (v.endsWith(` ${p}`) || p.endsWith(` ${v}`)) score = Math.max(score, 80);
          else if (` ${v} `.includes(` ${p} `) || ` ${p} `.includes(` ${v} `)) score = Math.max(score, 60);
        }
      }
      return { ing, score };
    })
    .filter((row) => row.score >= 60)
    .sort((a, b) => b.score - a.score || b.ing.name.length - a.ing.name.length);

  if (!scored.length) return undefined;
  if (scored.length > 1 && scored[0].score === scored[1].score && scored[0].score < 100) {
    return undefined;
  }
  return scored[0].ing;
}

function lineFromPantry(hit: Ingredient | undefined, sourceName: string, sortOrder: number): MapperRecipeLine {
  return {
    ingredient_id: hit?.id ?? "",
    ingredient_name: hit?.name ?? "",
    ingredient_brand: hit?.brand ?? "",
    ingredient_photo_url: hit?.photo_url ?? "",
    pack_size: hit?.pack_size ?? null,
    pack_label: hit?.pack_label ?? "",
    quantity: 10,
    unit: hit?.unit ?? "g",
    photo_url: hit?.photo_url ?? "",
    sort_order: sortOrder,
    source_name: sourceName,
  };
}

export function mergeDishIngredientsWithRecipe(
  dishTokens: string[],
  lines: RecipeLine[],
  pantry: Ingredient[],
): MapperRecipeLine[] {
  const remaining = [...lines];
  const rows: MapperRecipeLine[] = [];

  const takeLine = (pred: (line: RecipeLine) => boolean): RecipeLine | undefined => {
    const idx = remaining.findIndex(pred);
    if (idx < 0) return undefined;
    return remaining.splice(idx, 1)[0];
  };

  for (const token of dishTokens) {
    const hit = matchPantryIngredient(token, pantry);
    const existing =
      takeLine((line) => namesMatch(line.ingredient_name, token)) ||
      (hit ? takeLine((line) => line.ingredient_id === hit.id) : undefined);
    if (existing) {
      rows.push({ ...existing, source_name: token });
      continue;
    }
    rows.push(lineFromPantry(hit, token, rows.length));
  }

  for (const leftover of remaining) {
    rows.push({
      ...leftover,
      source_name: leftover.ingredient_name,
    });
  }

  return rows;
}

export function applyPantryToUnmappedLines(
  lines: MapperRecipeLine[],
  pantry: Ingredient[],
): MapperRecipeLine[] {
  return lines.map((line) => {
    if (line.ingredient_id) return line;
    const hit = matchPantryIngredient(line.source_name || line.ingredient_name, pantry);
    return hit ? { ...lineFromPantry(hit, line.source_name || hit.name, line.sort_order ?? 0), quantity: line.quantity || 10 } : line;
  });
}

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function usd(amount: number): string {
  return dollars.format(amount);
}

export function pct(ratio: number, digits = 1): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}

export function words(snakeCase: string): string {
  return snakeCase.replaceAll("_", " ");
}

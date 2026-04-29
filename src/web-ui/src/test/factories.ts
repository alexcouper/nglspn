export interface TokenPair {
  access: string;
  refresh: string;
}

let tokenCounter = 0;

export function makeTokenPair(overrides: Partial<TokenPair> = {}): TokenPair {
  tokenCounter += 1;
  return {
    access: `access-token-${tokenCounter}`,
    refresh: `refresh-token-${tokenCounter}`,
    ...overrides,
  };
}

export function seedTokens(tokens: TokenPair) {
  localStorage.setItem("access_token", tokens.access);
  localStorage.setItem("refresh_token", tokens.refresh);
}

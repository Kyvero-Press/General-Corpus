export function localSourceCacheEnabled(value: string | undefined): boolean {
  return value?.trim().toLowerCase() !== "false";
}

export function showLocalSourceCache(): boolean {
  return localSourceCacheEnabled(import.meta.env.VITE_SHOW_LOCAL_SOURCE_CACHE);
}

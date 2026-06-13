// ---------------------------------------------------------------------------
// Deterministic thumbnail URL convention (C6 Wave B / Thread 3, decision Q4)
//
// Every catalog tool's LIVE thumbnail lives at a deterministic public-read S3
// key: thumbnails/<cgspace_id>.png. The card/detail derive this URL from the
// tool's cgspace_id (== `id` in the static catalog) and attempt to load it,
// falling back to the existing letter-avatar onError. Only APPROVED images
// exist at the live key, so a 403/404 for un-approved tools simply triggers the
// graceful fallback — no tools.ts regeneration is needed per batch.
//
// If the backend has set cover_image_url (set on approve), prefer that explicit
// value; otherwise fall back to the derived convention URL.
// ---------------------------------------------------------------------------

const THUMBS_BUCKET =
  (import.meta.env.VITE_THUMBNAILS_BUCKET as string | undefined) ||
  'ee-toolbox-thumbnails-919959486181';
const THUMBS_REGION =
  (import.meta.env.VITE_THUMBNAILS_REGION as string | undefined) || 'eu-central-1';

/** Derived live thumbnail URL for a given cgspace_id (== catalog `id`). */
export function deriveThumbnailUrl(cgspaceId: string | null | undefined): string | null {
  if (!cgspaceId) return null;
  return `https://${THUMBS_BUCKET}.s3.${THUMBS_REGION}.amazonaws.com/thumbnails/${cgspaceId}.png`;
}

/**
 * Resolve the best thumbnail src for a tool: an explicit cover_image_url if the
 * backend set one, else the deterministic convention URL derived from its id.
 */
export function resolveThumbnailSrc(tool: {
  cover_image_url?: string | null;
  cgspace_id?: string | null;
  id?: string | null;
}): string | null {
  if (tool.cover_image_url) return tool.cover_image_url;
  return deriveThumbnailUrl(tool.cgspace_id ?? tool.id ?? null);
}

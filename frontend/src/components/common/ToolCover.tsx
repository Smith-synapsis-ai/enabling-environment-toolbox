import { useState } from 'react';
import { resolveThumbnailSrc } from '../../utils/thumbnailUrl';

// ---------------------------------------------------------------------------
// ToolCover (C6 Wave B / Thread 3) — renders a tool's thumbnail from the
// deterministic S3 URL convention with the EXISTING letter-avatar fallback.
//
// The catalog browse UI reads the static tools.ts (cover_image_url: null for
// un-approved tools), so we derive the live thumbnail URL from cgspace_id and
// attempt to load it; on a 403/404 (no approved image yet) we fall back to the
// letter avatar via onError. Approved tools render their real image with zero
// tools.ts regeneration. Used by both the catalog card and the detail panel.
// ---------------------------------------------------------------------------

interface ToolCoverProps {
  tool: { cover_image_url?: string | null; cgspace_id?: string | null; id?: string | null; title: string };
  bgColor: string;
  /** Tailwind height/extra classes for the image + placeholder wrapper. */
  className?: string;
  /** Tailwind classes for the inner letter-avatar circle. */
  avatarClassName?: string;
}

export default function ToolCover({
  tool,
  bgColor,
  className = 'w-full h-40',
  avatarClassName = 'w-14 h-14 text-lg',
}: ToolCoverProps) {
  const src = resolveThumbnailSrc(tool);
  const [failed, setFailed] = useState(false);

  if (src && !failed) {
    return (
      <img
        src={src}
        alt={tool.title}
        className={`${className} object-cover`}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <div
      className={`${className} flex items-center justify-center`}
      style={{ backgroundColor: bgColor + '12' }}
    >
      <div
        className={`${avatarClassName} rounded-full flex items-center justify-center text-white font-bold`}
        style={{ backgroundColor: bgColor }}
      >
        {tool.title.charAt(0)}
      </div>
    </div>
  );
}

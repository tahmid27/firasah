// Shared by the server card and the client sort menu. Plain values imported
// from a "use client" file reach the server only as references, not the
// object, so they live here.
export const SORTS = {
  engagement_rate: "Engagement rate",
  reach: "Reach",
  views: "Views",
  likes: "Likes",
  posted_at: "Newest",
} as const;
export type Sort = keyof typeof SORTS;

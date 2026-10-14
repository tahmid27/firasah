-- One row per post across every social platform (TikTok + Instagram),
-- ready to chart. Deduplicated to the latest-known version of each post
-- (a post's own stats, e.g. like_count, change between pulls — this keeps
-- only the most recent one, not every historical snapshot of it).
select * from {{ ref('int_social_posts_unioned') }}

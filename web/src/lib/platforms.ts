// Each platform keeps the same chart colour everywhere, whatever else is on
// the chart (colour follows the entity, not its position).
export const PLATFORM_COLOURS: Record<string, string> = {
  justgiving: "var(--series-1)",
  launchgood: "var(--series-2)",
  instagram: "var(--series-1)",
  tiktok: "var(--series-2)",
};

export const PLATFORM_NAMES: Record<string, string> = {
  justgiving: "JustGiving",
  launchgood: "LaunchGood",
  instagram: "Instagram",
  tiktok: "TikTok",
  mailchimp: "Mailchimp",
};

export function platformName(key: string) {
  return PLATFORM_NAMES[key] ?? key;
}

// The platforms' own labels for where a donation came from, in plain words.
const TRAFFIC_LABELS: Record<string, string> = {
  "justgiving:Direct": "Direct to your page",
  "justgiving:SponsoredDonationCampaign": "Supporters' fundraising pages",
  "launchgood:internal_comm_page": "LaunchGood community page",
  "launchgood:campaign_page": "Campaign page",
  "launchgood:whatsapp": "WhatsApp",
  "launchgood:facebook": "Facebook",
  "launchgood:instagram": "Instagram",
  "launchgood:email": "Email",
  "launchgood:twitter": "X (Twitter)",
  "launchgood:direct": "Direct link",
};

export function trafficLabel(source: string, traffic: string | null) {
  if (!traffic) return "Not recorded";
  const known = TRAFFIC_LABELS[`${source}:${traffic}`];
  if (known) return known;
  const words = traffic
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

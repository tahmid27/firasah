import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = { title: "Privacy policy · Firasah" };

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy policy" updated="22 November 2026">
      <p>
        Firasah is an analytics service for UK charities, run by Tahmid Naser as
        an individual. This page explains what data the service handles and
        why. Questions: tahmidnaser@outlook.com.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Account details:</strong> your email address and a password
          (stored hashed by our login provider, Supabase). We never see your
          password in readable form.
        </li>
        <li>
          <strong>Charity data you connect:</strong> fundraising, social media
          and email-marketing figures from the accounts your charity
          authorises (for example JustGiving, LaunchGood exports, Instagram,
          TikTok and Mailchimp). This can include donation amounts, dates, Gift
          Aid flags and, where the platform provides them, donor names and
          email addresses.
        </li>
        <li>
          <strong>Technical logs:</strong> request logs from our hosting
          provider (such as time, page and error codes), used to keep the
          service running.
        </li>
      </ul>

      <h2>How we use it</h2>
      <p>
        Only to show your charity its own dashboards and to keep the service
        working. We do not sell data, use it for advertising, or combine one
        charity&apos;s data with another&apos;s. Each charity can see only its
        own data.
      </p>

      <h2>Social media permissions</h2>
      <p>
        When you connect Instagram or TikTok, we request read-only access to
        the account&apos;s posts, statistics and audience insights. We do not
        post, message or change anything on those accounts. Access can be
        removed at any time in the platform&apos;s own settings, or by
        contacting us.
      </p>

      <h2>Where it is stored</h2>
      <p>
        Data is held on Google Cloud (BigQuery and Cloud Run, in the UK and
        Belgium) and Supabase (London). Access tokens are kept as secrets and
        are never written to logs.
      </p>

      <h2>Cookies and local storage</h2>
      <p>
        We use one cookie to keep you signed in, and your browser&apos;s local
        storage to remember your theme and sidebar choice. There are no
        advertising or analytics cookies.
      </p>

      <h2>Charities and donors</h2>
      <p>
        For donor data, the charity decides why and how it is used (the
        &quot;controller&quot; under UK GDPR) and Firasah processes it on the
        charity&apos;s behalf. Donors who want to see or erase their data
        should contact the charity.
      </p>

      <h2>Your rights</h2>
      <p>
        You can ask to see, correct or delete your data, or to close your
        account, by emailing us. We will delete a charity&apos;s data within
        30 days of a request. You can also complain to the Information
        Commissioner&apos;s Office (ico.org.uk).
      </p>

      <h2>The demo</h2>
      <p>
        The &quot;Click here for demo&quot; account shows entirely fictional,
        computer-generated data. No real person or charity is represented.
      </p>

      <h2>Changes</h2>
      <p>
        If this policy changes, the date above changes with it.
      </p>
    </LegalPage>
  );
}

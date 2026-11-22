import type { Metadata } from "next";

import { LegalPage } from "@/components/legal-page";

export const metadata: Metadata = { title: "Terms of use · Firasah" };

export default function TermsPage() {
  return (
    <LegalPage title="Terms of use" updated="22 November 2026">
      <p>
        Firasah is an analytics service for UK charities, run by Tahmid Naser
        as an individual. By using it you agree to these terms. Questions:
        tahmidnaser@outlook.com.
      </p>

      <h2>The service</h2>
      <p>
        Firasah collects data from the platforms a charity connects and shows
        it in dashboards. It is currently in an early, invitation-only beta and
        is provided as is. We aim to keep it running and accurate but do not
        guarantee availability, and figures such as open rates depend on the
        platforms&apos; own data and can be approximate.
      </p>

      <h2>Your account</h2>
      <ul>
        <li>Keep your login details private; you are responsible for activity under your account.</li>
        <li>Only connect accounts your charity is entitled to connect.</li>
        <li>Do not try to access another charity&apos;s data or interfere with the service.</li>
      </ul>

      <h2>Your data</h2>
      <p>
        Your charity keeps ownership of its data. You give us permission to
        read and process it to provide the service, as described in the{" "}
        <a href="/privacy" className="underline">
          privacy policy
        </a>
        . Platform connections are read-only and can be removed at any time.
      </p>

      <h2>Limits</h2>
      <p>
        The dashboards are for information and are not financial, tax or legal
        advice. Check figures such as Gift Aid before relying on them for
        claims. To the extent the law allows, we are not liable for losses
        arising from use of the service.
      </p>

      <h2>Ending use</h2>
      <p>
        You can stop at any time and ask us to delete your data. We may
        suspend access for misuse or if the service is withdrawn, with
        reasonable notice where possible.
      </p>

      <h2>Demo</h2>
      <p>
        The demo account uses fictional data and is shared by all visitors.
        Please do not enter personal information anywhere in it.
      </p>

      <h2>Law</h2>
      <p>These terms are governed by the laws of England and Wales.</p>
    </LegalPage>
  );
}

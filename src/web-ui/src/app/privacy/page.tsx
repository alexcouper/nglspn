import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy - Naglasúpan",
};

export default function PrivacyPolicyPage() {
  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-lg font-semibold text-foreground tracking-tight mb-6">
          Privacy Policy
        </h1>
        <p className="text-xs text-muted-foreground mb-8">
          Last updated: 22 February 2025
        </p>

        <div className="space-y-8 text-sm text-foreground leading-relaxed">
          <div>
            <h2 className="font-semibold mb-2">Who we are</h2>
            <p>
              Naglasúpan is a platform for Iceland-based developers to showcase
              their projects, participate in competitions, and connect with the
              local tech community. The site is operated from Iceland.
            </p>
          </div>

          <div>
            <h2 className="font-semibold mb-2">What data we collect</h2>
            <p className="mb-2">
              When you create an account, we collect:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Email address</li>
              <li>First and last name</li>
              <li>Kennitala (Icelandic national ID number)</li>
              <li>A password (stored securely as a hash, never in plain text)</li>
            </ul>
            <p className="mt-3 mb-2">
              When you submit a project, we collect:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Project details (title, description, URLs, tech stack)</li>
              <li>Images you upload</li>
            </ul>
            <p className="mt-3 mb-2">
              When anyone views a project page, we record:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>The visitor&apos;s IP address and browser user-agent string,
                used solely to produce an accurate view count (one count per
                unique visitor)</li>
            </ul>
          </div>

          <div>
            <h2 className="font-semibold mb-2">How we use your data</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>To operate your account and let you manage your projects</li>
              <li>To display approved projects publicly on the platform</li>
              <li>To run competitions and communicate results</li>
              <li>To send you emails you have opted in to (platform updates,
                competition results)</li>
              <li>To generate aggregate view counts for projects</li>
            </ul>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Data sharing</h2>
            <p>
              We do not share your personal data with any third parties.
            </p>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Project promotion</h2>
            <p>
              Projects submitted to Naglasúpan may be promoted on external
              platforms (for example, LinkedIn or social media) to support the
              Icelandic developer community. If you prefer your projects not to
              be featured externally, you can opt out at any time in your
              profile settings.
            </p>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Where your data is stored</h2>
            <p>
              Your data is stored on servers operated by Scaleway, located in
              France (EU). Uploaded images are served through a CDN. All data
              transfers are encrypted in transit using TLS.
            </p>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Cookies and tracking</h2>
            <p>
              We do not use any third-party analytics or tracking services. The
              site uses only the cookies strictly necessary for authentication
              and session management.
            </p>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Your rights</h2>
            <p className="mb-2">You have the right to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Access the personal data we hold about you</li>
              <li>Correct any inaccurate data</li>
              <li>Request deletion of your account and associated data</li>
              <li>Opt out of promotional emails and external project promotion
                via your profile settings</li>
            </ul>
          </div>

          <div>
            <h2 className="font-semibold mb-2">Contact</h2>
            <p>
              If you have questions about this policy or wish to exercise your
              rights, contact us at{" "}
              <a
                href="mailto:alex@naglasupan.is"
                className="text-accent hover:text-accent-hover transition-colors"
              >
                alex@naglasupan.is
              </a>.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

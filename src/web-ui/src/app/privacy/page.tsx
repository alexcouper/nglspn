import type { Metadata } from "next";
import html from "remark-html";
import { remark } from "remark";

export const metadata: Metadata = {
  title: "Privacy Policy - Naglasúpan",
};

const content = `
# Privacy Policy

*Last updated: 23 February 2025*

## Who we are

Naglasupan is a community platform for Iceland-based developers. The site is operated from Iceland.

## What we collect

We collect the personal information you provide when you create an account or use the platform. This includes things like your name, contact details, identity verification, and any content you choose to submit or interact with.

We also collect technical data automatically when you use the site, such as your IP address and browser information. This is used for security, to operate the service, and to understand how the platform is used in aggregate.

Passwords are stored securely as hashes and are never kept in plain text.

## How we use it

We use your data to operate and improve the platform. This includes running your account, displaying content you publish, communicating with you about things you have opted in to, and monitoring the health and performance of the service.

We do not use third-party analytics or advertising services.

## Data sharing

We do not sell or share your personal data with third parties.

Content you publish on the platform is public by nature. Projects and other public content may be promoted on external channels (such as social media) to support the Icelandic developer community. You can opt out of external promotion in your profile settings.

## Where your data is stored

Your data is stored on servers located in the EU. All data is encrypted in transit.

## Cookies and tracking

We use only the cookies necessary to keep you logged in. We collect anonymous performance metrics to maintain site reliability. We do not use any third-party tracking.

## Your rights

You can access, correct, or delete your personal data at any time. You can manage your communication and promotion preferences in your profile settings. To exercise any of these rights, contact us.

## Contact

If you have questions about this policy, contact us at [alex@naglasupan.is](mailto:alex@naglasupan.is).
`;

async function processMarkdown(markdown: string) {
  const file = await remark().use(html).process(markdown);
  return file.toString();
}

export default async function PrivacyPolicyPage() {
  const contentHtml = await processMarkdown(content);

  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <article className="article markdown">
          <div dangerouslySetInnerHTML={{ __html: contentHtml }} />
        </article>
      </div>
    </section>
  );
}

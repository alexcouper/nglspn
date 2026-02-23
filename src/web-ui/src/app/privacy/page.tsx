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

Naglasupan is a platform for Iceland-based developers to showcase their projects, participate in competitions, and connect with the local tech community. The site is operated from Iceland.

## What data we collect

When you create an account, we collect:

- Email address
- First and last name
- Kennitala (Icelandic national ID number)
- A password (stored securely as a hash, never in plain text)

When you use the platform, we may collect:

- Content you submit, such as projects, comments, reactions, announcements, and any associated images or links
- Your preferences and settings

When anyone views a project page, we record:

- The visitor's IP address and browser user-agent string, used solely to produce an accurate view count (one count per unique visitor)

## How we use your data

- To operate your account and let you manage your content
- To display approved content publicly on the platform
- To run competitions and communicate results
- To send you emails you have opted in to (platform updates, competition results)
- To generate aggregate view counts and usage statistics
- To monitor and improve platform performance and reliability

## Data sharing

We do not share your personal data with any third parties.

## Project promotion

Projects submitted to Naglasupan may be promoted on external platforms (for example, LinkedIn or social media) to support the Icelandic developer community. If you prefer your projects not to be featured externally, you can opt out at any time in your profile settings.

## Where your data is stored

Your data is stored on servers operated by Scaleway, located in France (EU). Uploaded images are served through a CDN. All data transfers are encrypted in transit using TLS.

## Cookies, tracking, and performance monitoring

We do not use any third-party analytics or tracking services. The site uses only the cookies strictly necessary for authentication and session management. We use OpenTelemetry to collect anonymous performance data (page load times, error rates) to help us improve the reliability of the platform. This data does not identify individual users.

## Your rights

You have the right to:

- Access the personal data we hold about you
- Correct any inaccurate data
- Request deletion of your account and associated data
- Opt out of promotional emails and external project promotion via your profile settings

## Contact

If you have questions about this policy or wish to exercise your rights, contact us at [alex@naglasupan.is](mailto:alex@naglasupan.is).
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

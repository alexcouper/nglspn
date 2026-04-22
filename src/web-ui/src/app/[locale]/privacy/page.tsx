import type { Metadata } from "next";
import ReactMarkdown from "react-markdown";

export const metadata: Metadata = {
  title: "Privacy Policy - Naglasúpan",
};

const content = `
# Privacy Policy

*Last updated: 25 February 2026*

## Who we are

Naglasúpan is a community platform for Iceland-based developers. The site is operated by Codalens ehf. (KT 570125-0280), registered in Iceland.

The data controller is Codalens ehf.

## What we collect

We collect the personal information you provide when you create an account or use the platform:

- **Account information**: your name, email address, and password.
- **Identity verification**: during signup, we verify your connection to the Icelandic developer community. This may involve checking your professional background. We do not store identity documents.
- **Content**: anything you choose to submit, publish, or interact with on the platform.

We also collect technical data automatically when you use the site, such as your IP address and browser information. This is used for security, to operate the service, and to understand how the platform is used in aggregate.

## Legal basis for processing

We process your personal data on the following grounds under the GDPR:

- **Contract**: to provide the service you signed up for (account, content publishing, communication).
- **Legitimate interest**: to maintain security, prevent abuse, and understand platform usage in aggregate.
- **Consent**: for optional features like email communications and external promotion of your content. You can withdraw consent at any time in your profile settings.

## How we use it

We use your data to operate and improve the platform. This includes running your account, displaying content you publish, communicating with you about things you have opted in to, and monitoring the health and performance of the service.

We do not use third-party analytics or advertising services.

## Data sharing

We do not sell your personal data.

To operate the platform, we use a limited number of third-party service providers (such as cloud hosting and email delivery). These processors only access data as necessary to provide their services and are bound by data processing agreements.

Content you publish on the platform is public by nature. Projects and other public content may be promoted on external channels (such as social media) to support the Icelandic developer community. You can opt out of external promotion in your profile settings.

## Where your data is stored

Your data is stored on servers located in the EU. All data is encrypted in transit. We take appropriate technical and organisational measures to protect your personal data.

## Data retention

We keep your personal data for as long as your account is active. If you delete your account, we will remove your personal data within 30 days. Published content that has been shared publicly may be retained in anonymised form. Backups containing personal data are purged on a rolling cycle.

We retain technical logs (such as IP addresses) for no longer than 90 days.

## Cookies and tracking

We use only the cookies necessary to keep you logged in. We collect anonymous performance metrics to maintain site reliability. We do not use any third-party tracking.

## Your rights

Under the GDPR, you have the right to:

- **Access** your personal data.
- **Correct** inaccurate or incomplete data.
- **Delete** your account and personal data.
- **Data portability** — receive your data in a structured, machine-readable format.
- **Restrict processing** of your data in certain circumstances.
- **Object** to processing based on legitimate interest.
- **Withdraw consent** at any time for consent-based processing.

You can manage your communication and promotion preferences in your profile settings. To exercise any of these rights, contact us.

If you believe your data protection rights have been violated, you have the right to lodge a complaint with the Icelandic Data Protection Authority ([Persónuvernd](https://www.personuvernd.is)).

## Changes to this policy

If we make material changes to this policy, we will notify registered users by email. The "last updated" date at the top of this page will always reflect the most recent revision.

## Contact

If you have questions about this policy, contact [admin@naglasupan.is](mailto:admin@naglasupan.is).
`;

export default function PrivacyPolicyPage() {
  return (
    <section className="py-12 px-4 sm:px-6 bg-white">
      <div className="max-w-3xl mx-auto">
        <article className="article markdown">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      </div>
    </section>
  );
}

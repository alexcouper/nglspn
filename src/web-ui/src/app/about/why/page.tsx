import ReactMarkdown from "react-markdown";

const why = `
We should be more ambitious in terms of what we can achieve here in Iceland.

There are lots of people here with side projects that they're working on, or with ideas that seem too fragile to see the light of day. But we need them.

We need them for the **solutions** they bring, for the **learning** and **collaboration** opportunities they offer, for the **jobs** they may create, and for the shared **infrastructure** they may facilitate the creation of.

Naglasúpan serves as a space that encourages Iceland-based developers to ship the things they're working on, to show it to others and to get feedback on it.
`;

const pocSection = `
We live at a time where POC creation has never been cheaper.

What we need is
 - to encourage more building
 - to provide accelerated feedback
 - to promote adoption of built products: wins in the community are wins for all of us.
`;

const seniorSection = `
Developing with AI has made cloning/improving senior developers more attractive than hiring and training juniors.

This inevitable short-termism needs addressing or Iceland faces a software development extinction event.

We need a way to encourage newer developers to build and ship things, to get feedback on them, and to grow.

If companies aren't willing to invest in the next generation, the community needs to.
`;

const geopoliticsSection = `
Iceland would be better off if more of our key services were built and hosted here.

We face increasing geopolitical risk, and we need to take steps to mitigate that.

Naglasúpan will begin by encouraging a community of builders to use each other's side projects but later hopes to identify opportunities for (and enable swarming on) building bigger shared infrastructure.
`;

export default function WhyPage() {
  return (
    <>
      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <article className="article markdown">
            <ReactMarkdown>{why}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-muted">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            PoC cost is almost zero
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{pocSection}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            Senior developer gap
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{seniorSection}</ReactMarkdown>
          </article>
        </div>
      </section>

      <section className="py-12 px-4 sm:px-6 bg-muted">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-foreground tracking-tight mb-4">
            Geopolitics &amp; Digital Sovereignty
          </h2>
          <article className="article markdown">
            <ReactMarkdown>{geopoliticsSection}</ReactMarkdown>
          </article>
        </div>
      </section>
    </>
  );
}

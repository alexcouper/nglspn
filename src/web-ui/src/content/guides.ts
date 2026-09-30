export type GuideSection = {
  id: string;
  title: string;
  body: string;
};

export type Guide = {
  slug: string;
  title: string;
  description: string;
  summary: string;
  kind: "hub" | "spoke";
  parent?: string;
  updated: string;
  sections: GuideSection[];
  related: string[];
  action: { href: string; label: string };
};

// Keep dates tied to substantive editorial changes, rather than build time.
export const guides: Guide[] = [
  {
    slug: "iceland-developer-community",
    kind: "hub",
    title: "What is Naglasúpan? Iceland’s software community",
    description: "Naglasúpan connects people building software in Iceland. Discover local side projects, learn the story behind the name, and find a way to contribute.",
    summary: "Naglasúpan is a community platform for people building software in Iceland. Discover Icelandic side projects, share your own work, and exchange feedback with other builders. You can take part by trying a project, asking a useful question, or offering a small contribution.",
    updated: "2026-09-29",
    sections: [
      {
        id: "why-the-name",
        title: "“Nagla súpa”: the story behind Naglasúpan",
        body: "Naglasúpa means “nail soup” in Icelandic; Naglasúpan means “the nail soup”. The name comes from a story about a traveller who starts making soup with a few nails. Curious villagers each bring something to add to the pot, until their small contributions become a shared meal. You can read the version that inspired this project in [Naglasúpan’s own introduction](https://github.com/alexcouper/nglspn#the-story-brief-mode).\n\nThat is the idea behind this software community in Iceland. One person brings a side project, another tries it and gives feedback, and someone else offers a skill. A contribution does not have to be large to help a project move forward.\n\nOn naglasupan.is, the shared work is software: [apps, tools, and experiments made by the community](/projects). Start with a project that interests you, or read [how to get involved](/guides/iceland-developer-community/get-involved) for a first step you can take today.",
      },
      {
        id: "start-with-projects",
        title: "Where can you discover what people in Iceland are building?",
        body: "The [project directory](/projects) is the starting point on Naglasúpan. Browse the projects, open something that interests you, and read what its creator says it does. A working demo, a screenshot, and a recent update tell you different things: what you can try, what it looks like, and what has changed.\n\nNaglasúpan focuses on work people are making and sharing. For a broader view of the startup ecosystem, [Northstack](https://www.northstack.is/about/) describes its reporting and community initiatives. These are different entry points into Iceland’s tech community; neither is a complete map of everyone building here.\n\nUse the [guide to finding Icelandic software projects](/guides/iceland-developer-community/find-projects) to turn a directory visit into a shortlist of things to try.",
      },
      {
        id: "choose-a-way-in",
        title: "Choose a way to participate",
        body: "You do not need a finished application to have something useful to offer. Choose an action that fits what you have today:\n\n- **Curiosity:** try a project and describe what you expected to happen.\n- **A project:** explain who it is for, show its current state, and ask one specific question.\n- **A skill:** offer a bounded task such as improving setup instructions or testing a screen on mobile.\n- **A discovery:** suggest someone else’s project as a tipoff and keep its creator clearly credited.\n\nFor an introduction you can adapt, read [how to join through a project](/guides/iceland-developer-community/get-involved). If you are ready to share your own work, move to the [side-project guide](/guides/share-a-side-project).",
      },
      {
        id: "understand-the-platform",
        title: "What does Naglasúpan help you do?",
        body: "Naglasúpan gives projects a public page and a place for discussion. Creators can describe their work and publish articles about it; interested people can follow projects. Community competitions provide another way to take part, with details on each [competition page](/competitions).\n\nCreating a draft, publishing a project, and entering a competition are separate steps. Publishing submits a project for review; it does not make it immediately visible or automatically enter it into a competition. Read the [sharing checklist](/guides/share-a-side-project/project-page-checklist) before submitting.\n\nThe longer-term ambition includes more collaboration and shared infrastructure. The [project’s purpose](/about/why) explains that direction; it should not be read as a list of services already available.",
      },
      {
        id: "make-it-useful",
        title: "Make your first interaction useful",
        body: "Pick one project, spend a few minutes understanding its purpose, and leave a message tied to something you actually tried. A report such as “I could find the map, but I could not tell how to add a marker on my phone” gives a creator something concrete to investigate.\n\nWhen you return, check whether the creator has replied or shared an update. A continuing conversation can be more useful than introducing yourself to many people at once. The [contribution guide](/guides/contribute-to-projects) explains how to turn that first interaction into a manageable piece of work.",
      },
    ],
    related: ["share-a-side-project", "contribute-to-projects"],
    action: { href: "/projects", label: "Explore the projects" },
  },
  {
    slug: "iceland-developer-community/find-projects",
    kind: "spoke",
    parent: "iceland-developer-community",
    title: "How to find Icelandic software and side projects",
    description: "Find Icelandic software projects by the problem they solve, assess what is ready to try, and follow the work that interests you.",
    summary: "Look for a problem you recognise, then inspect the project’s description, demo, and updates. Naglasúpan’s directory is a starting point for finding software made by Iceland’s builder community, from early experiments to live tools.",
    updated: "2026-09-29",
    sections: [
      {
        id: "search-by-problem",
        title: "Start with the problem, then explore the technology",
        body: "Open the [project directory](/projects) with a question in mind: is there something that helps with a task you do, a topic you care about, or a skill you want to learn? Browse categories and project descriptions before narrowing your attention to a particular programming language.\n\nFor a concrete example, [Fundið’s project page](/projects/fundid-is) describes a map-based lost-and-found service for Iceland. It is a useful illustration of finding a project through an everyday problem. Check the project page and linked website for its current capabilities; a directory description is a starting point for exploration, not an independent product review.",
      },
      {
        id: "read-the-signals",
        title: "What should you check before trying a project?",
        body: "Read the creator’s description of its stage and look for a route to a demo or website. An early prototype may be useful for giving feedback even if it is not ready for everyday use. A live service may still have known limitations.\n\n- **Purpose:** can you explain who the project is for?\n- **Access:** can you try it, or is the page showing work in progress?\n- **Activity:** do updates or discussions explain what is happening now?\n- **Help wanted:** has the creator said what kind of feedback or contribution would be useful?\n\nA quiet update feed does not prove a project is abandoned. If its status matters to you, ask its creator rather than inferring it from a date alone.",
      },
      {
        id: "try-one-task",
        title: "Try one task and record what happens",
        body: "Choose a small task that matches the project’s stated purpose. Write down where you started, what you did, and whether you reached the expected result. Use sample information when exploring a tool for the first time.\n\nIf the task fails, note the screen, device, and steps needed to reproduce the problem. If it works, say which part helped you. Both kinds of observations are more informative than a general rating. The [feedback guide](/guides/share-a-side-project/get-useful-feedback) includes a report format you can reuse.",
      },
      {
        id: "keep-in-touch",
        title: "Follow up or suggest a project that is missing",
        body: "Follow projects you want to revisit and use their discussions to ask focused questions. If you would like to help, first check for a repository or contribution instructions linked by the creator; being listed on Naglasúpan does not mean a project is open source.\n\nIf you know a project made by someone else that belongs in the community, the [create page](/create) offers a **Tipoff** option. Sign in, provide its URL, and credit its maker accurately. A suggestion should help people find the original work. It does not make you the owner or establish that the maker is recruiting collaborators.",
      },
    ],
    related: ["iceland-developer-community/get-involved", "contribute-to-projects/first-contribution"],
    action: { href: "/projects", label: "Find a project to try" },
  },
  {
    slug: "iceland-developer-community/get-involved",
    kind: "spoke",
    parent: "iceland-developer-community",
    title: "How to get involved in Iceland’s builder community",
    description: "Join the conversation through a project: introduce yourself, give useful feedback, or offer a small contribution without needing a finished app.",
    summary: "A useful introduction connects your interest to someone’s work. Choose a project, explain what you tried or noticed, and propose one small next step. You can contribute as a developer, designer, writer, tester, or interested user.",
    updated: "2026-09-29",
    sections: [
      {
        id: "choose-a-role",
        title: "You can take part before you have a project",
        body: "Start as a user if you are unsure what to offer. Try a workflow and explain what was clear or confusing. If you enjoy writing, check whether the description or setup instructions make sense to a newcomer. If you know the problem domain, describe a real situation the builder may not have considered.\n\nThese are suggestions for ways to help, not standing invitations from every creator. Read the project’s own request first. A narrow, relevant offer gives someone an easier decision than a broad promise to help with anything.",
      },
      {
        id: "write-an-introduction",
        title: "An introduction you can adapt",
        body: "Use this example as a structure, replacing the details with something you actually did:\n\n> Hi, I’m learning frontend development and tried your project on my phone. I got through the first step, but could not tell whether my changes had saved. Would a short screen recording of that flow be useful? I can put one together this weekend.\n\nThe message explains your context, names an observation, asks a question, and sets a modest expectation. A creator can accept, redirect, or decline without having to invent a task for you.\n\nFor a broader introduction, the [contact page](/about/contact) links to community contact options. Keep project-specific questions attached to the project when possible so others can learn from the answer.",
      },
      {
        id: "make-the-commitment-small",
        title: "Agree on a small first step",
        body: "Before beginning, confirm what you will deliver and how the creator wants to receive it. A screenshot with notes, a documentation edit, or a reproducible bug report can be a complete contribution. You do not need to commit to a long-running collaboration immediately.\n\nIf the work grows, pause and agree on the next piece. Make your availability explicit and say when you need to step away. See the [first-contribution checklist](/guides/contribute-to-projects/first-contribution) for a more detailed sequence.",
      },
      {
        id: "share-your-own-work",
        title: "Bring your own work into the conversation",
        body: "When you have something to show, explain the problem and its current state. A specific request such as “Can you tell whether this screen explains the next step?” is easier to respond to than “Any thoughts?”\n\nThe [guide to sharing a side project](/guides/share-a-side-project) covers preparing a page, submitting it for review, and following up. If you are interested in a community competition, read that competition’s details and enter separately. Being part of the directory and taking part in a competition are distinct choices.",
      },
    ],
    related: ["contribute-to-projects", "share-a-side-project/get-useful-feedback"],
    action: { href: "/projects", label: "Meet builders through their projects" },
  },
  {
    slug: "share-a-side-project",
    kind: "hub",
    title: "How to share a side project and get useful feedback",
    description: "Prepare a clear project page, share your side project with Iceland’s builder community, and turn feedback into a manageable next step.",
    summary: "Share the problem, the current state of your project, and one question you want help answering. On Naglasúpan, you start with a draft, prepare your project page, and submit it for review. Competition entry is a separate action.",
    updated: "2026-09-29",
    sections: [
      {
        id: "what-to-share",
        title: "What should you share before a project feels finished?",
        body: "Share a version that gives another person something concrete to understand or try. That might be a limited demo or a page with screenshots and a clear explanation of what works. State what is missing so people do not mistake a prototype for a complete service.\n\nDecide what you want to learn before writing the page. Are people confused by the problem statement? Can they complete the main task? Does the result solve the problem you intended? One of these questions is enough for an initial request.\n\nUse the [project-page checklist](/guides/share-a-side-project/project-page-checklist) to turn those decisions into a readable description and a usable demonstration.",
      },
      {
        id: "publish-on-naglasupan",
        title: "How do you add a project to Naglasúpan?",
        body: "Sign in and open [Create a project](/create). Enter the project URL and choose **Mine** if you made it. Creating the project starts a draft that you can prepare before publishing. If you are suggesting someone else’s work, choose **Tipoff** instead and keep attribution clear.\n\nComplete the project information in the editor and use its publishing checks to resolve missing details. Publishing submits the project for approval. Until that review is complete, do not assume the project is visible in the public directory. You can return to your work through [My Projects](/my-projects).\n\nIf you want to enter a competition, review its details and make that choice separately. Adding a project does not automatically enter it into a round, and acceptance into the directory does not guarantee a competition result.",
      },
      {
        id: "ask-a-focused-question",
        title: "Ask for feedback that can change a decision",
        body: "“What do you think?” leaves the reviewer to choose the task. Instead, describe a short scenario and ask for observations: “Try finding an item near you. Where did you expect the location filter to be?”\n\nGive people a realistic amount of work and tell them where to respond. Ask permission before turning a private response into a public testimonial or example. The [useful-feedback guide](/guides/share-a-side-project/get-useful-feedback) includes a request template and a way to sort the responses.",
      },
      {
        id: "close-the-loop",
        title: "Share what you learned next",
        body: "After people respond, group the observations by the task they were trying to complete. Choose one change, explain the reason, and give people a route to try the revised version. If you decide against a suggestion, a brief explanation still closes the loop.\n\nProject articles can record a change, an experiment, or a lesson. Keep the update specific: what was difficult, what changed, and what remains unresolved. Over time, that gives new visitors context that a screenshot alone cannot provide. If feedback reveals a task you cannot tackle alone, use the [collaboration-brief guide](/guides/contribute-to-projects/find-collaborators) to define an offer someone can respond to.",
      },
    ],
    related: ["iceland-developer-community", "contribute-to-projects/find-collaborators"],
    action: { href: "/create", label: "Start a project draft" },
  },
  {
    slug: "share-a-side-project/project-page-checklist",
    kind: "spoke",
    parent: "share-a-side-project",
    title: "A side-project page checklist and description template",
    description: "Write a side-project description that explains the problem, shows what works, credits contributors, and asks for specific feedback.",
    summary: "A useful project page answers five questions: who is it for, what does it help them do, what works today, how can someone try it, and what feedback would help? Make those answers easy to find before adding a long technical history.",
    updated: "2026-09-29",
    sections: [
      {
        id: "lead-with-the-task",
        title: "Lead with the task your project helps someone do",
        body: "Write a sentence that connects a person, a task, and an outcome. As an illustrative example: “A shared rehearsal planner that helps small bands find a time everyone can make.” That tells a visitor more than “An innovative full-stack scheduling platform.”\n\nThen describe the current stage in plain language: a clickable prototype, a working first version, or a service people can use today. Explain significant limitations next to the capabilities they affect. Keep technical details for readers who want to understand how it was built or contribute.",
      },
      {
        id: "description-template",
        title: "Copy this project-description structure",
        body: "Replace each prompt with facts about your project. These prompts are an editorial checklist, not a list of mandatory fields in the editor.\n\n- **The problem:** Who encounters it, and what is difficult today?\n- **The project:** What can someone do with it?\n- **Current state:** What works, and what is still experimental or missing?\n- **Try it:** Where should someone begin, and what example task should they attempt?\n- **Feedback wanted:** What is the one question you need answered next?\n- **Contributors:** Who made it, and how should their work be credited?\n- **Technical context:** Which technologies or repository links would help a contributor?\n\nDo not fill gaps with projected usage, unsupported results, or features you have not built. A clear limitation helps a visitor give relevant feedback.",
      },
      {
        id: "show-the-work",
        title: "Choose screenshots that explain the experience",
        body: "Show the core task in a real screen. A logo establishes identity, while a screenshot can explain what the user actually does. Include enough surrounding context to make the screen understandable and remove private information from the image.\n\nCheck the page on a narrow screen. Read the description without assuming the visitor knows your terminology. Open the demo link in a signed-out browser and verify that the stated starting point is reachable. If access is limited, explain that before asking someone to try it.",
      },
      {
        id: "before-publishing",
        title: "Before submitting your Naglasúpan page",
        body: "Confirm the URL, description, images, and credits. Use the editor’s own publishing checks for the current required fields; this checklist helps with clarity, while the interface determines whether the draft is ready to submit.\n\nPublishing sends a draft for review. Wait for approval before telling others it is available in the public directory. When it is visible, share the public project link with a focused request using the [feedback template](/guides/share-a-side-project/get-useful-feedback). If a competition is relevant, review the round and enter separately rather than assuming publication includes entry.",
      },
    ],
    related: ["share-a-side-project/get-useful-feedback", "contribute-to-projects/find-collaborators"],
    action: { href: "/create", label: "Create your project draft" },
  },
  {
    slug: "share-a-side-project/get-useful-feedback",
    kind: "spoke",
    parent: "share-a-side-project",
    title: "How to get useful feedback on a side project",
    description: "Ask a focused question, give testers a realistic task, and turn their observations into your next side-project improvement.",
    summary: "Useful feedback starts with a task and a decision. Tell someone what to try, ask what happened, and explain what you are trying to learn. Record observations separately from suggested solutions so you can decide what to change.",
    updated: "2026-09-29",
    sections: [
      {
        id: "choose-one-question",
        title: "Choose the question before asking for opinions",
        body: "Different questions need different reviewers. Someone who has the problem can explain whether the workflow fits their needs. Someone new to the topic can show where the explanation breaks down. A developer can help inspect a technical failure.\n\nWrite down the decision you will make after the conversation. For example: “Should I explain the map before asking people to add an item?” You can then ask a reviewer to attempt that task instead of asking whether the whole product is good. A small number of conversations can reveal useful problems, but does not establish how common those problems are across your audience.",
      },
      {
        id: "request-template",
        title: "A feedback request you can reuse",
        body: "Adapt this example to a task your project supports:\n\n> I’m testing whether the first-use flow makes sense. Could you open the demo and try creating one example entry? Please tell me where you hesitated, what you expected, and whether you reached the confirmation screen. The example data is disposable. A few sentences in this project discussion would help.\n\nInclude the relevant link and mention any access requirements. Avoid explaining every interaction in advance if you want to learn whether the screen is understandable. If the user gets stuck, note the point of confusion before helping them continue.",
      },
      {
        id: "record-observations",
        title: "Separate what happened from how to fix it",
        body: "Keep a simple record for each response:\n\n- **Task:** what the reviewer tried to do.\n- **Observation:** what happened or where they hesitated.\n- **Context:** device, browser, relevant experience, or access issue.\n- **Suggestion:** any solution they proposed.\n- **Next step:** investigate, change, ask a follow-up question, or defer.\n\n“Could not find the save action” is an observation. “Make the button green” is a suggested solution. The observation may be valuable even if another solution fits the interface better. When reporting a bug, add the shortest sequence of steps that reproduces it and the expected result.",
      },
      {
        id: "respond-and-retest",
        title: "Acknowledge the response and test the change",
        body: "Thank the person for the specific thing they helped you see. Explain the change you made, or why you are deferring it. Then invite them to retry the same task if they have time. Avoid treating positive comments as evidence of adoption or publishing private feedback without permission.\n\nOn Naglasúpan, keep the request close to the project and use an article when you have a fuller lesson to share. For example, explain the confusing interaction, the revision, and what you still need to check. If the work needs another person’s skills, write a [bounded collaboration brief](/guides/contribute-to-projects/find-collaborators) so the next request is equally clear.",
      },
    ],
    related: ["share-a-side-project/project-page-checklist", "contribute-to-projects/first-contribution"],
    action: { href: "/my-projects", label: "Open your projects" },
  },
  {
    slug: "contribute-to-projects",
    kind: "hub",
    title: "How to contribute to a community software project",
    description: "Find a useful first contribution, agree on its scope, and collaborate with software builders through code, documentation, design, or testing.",
    summary: "Start by understanding the project and asking what would help. Agree on one small contribution, follow the creator’s instructions, and leave enough context for them to review it. Contributions can include testing, writing, design, or code.",
    updated: "2026-09-29",
    sections: [
      {
        id: "find-a-fit",
        title: "Choose a project you can understand and use",
        body: "Browse [projects on Naglasúpan](/projects) and choose one whose problem interests you. Try the main workflow or read the documentation before proposing changes. That gives your offer a connection to the project’s actual needs.\n\nCheck the creator’s links for contribution instructions and open tasks. A public project listing is not an invitation to change its code, and it does not establish an open-source licence. If no route to contributing is documented, ask a concise question in the project discussion.\n\nThe [first-contribution checklist](/guides/contribute-to-projects/first-contribution) walks through choosing a task and preparing a useful handoff.",
      },
      {
        id: "choose-the-contribution",
        title: "What can you contribute besides code?",
        body: "A useful contribution removes a specific obstacle for the people building or using the project. That may mean documenting a setup step, reproducing a bug, explaining a confusing term, testing a mobile layout, or reviewing an Icelandic translation. Ask whether that work is wanted before starting a large revision.\n\nGitHub’s [Open Source Guides](https://opensource.guide/how-to-contribute/) describe several ways to participate and how to approach a project. Use the project’s own instructions as the authority for where to submit work and how reviews happen. The guidance here also applies to collaboration where the code itself is not publicly available.",
      },
      {
        id: "agree-on-scope",
        title: "Agree on the task and the review",
        body: "Before working, establish the intended result, the person who will review it, and a realistic time commitment. “Check the sign-up flow on a small screen and send annotated screenshots” is easier to evaluate than “Improve the UX.”\n\nIf access or a technical decision is blocking you, say so early. A small contribution should have a stopping point: a report delivered, an edit reviewed, or a change tested. Finishing one small task gives both sides a basis for deciding whether to continue.\n\nIf you are the creator seeking help, use the [collaborator brief](/guides/contribute-to-projects/find-collaborators) to make those expectations visible.",
      },
      {
        id: "leave-a-good-handoff",
        title: "Make the handoff easy to review",
        body: "Describe what changed, why, and how you checked it. Include screenshots for a visual issue and reproduction steps for a bug. Keep unrelated ideas in a separate note so the reviewer can assess one task at a time.\n\nBe open about unfinished parts and decisions you need help with. A contribution is an offer for review; its creator may ask for changes or choose another approach. When the work is accepted, agree on credit and record anything a future contributor will need to know. That documentation makes the next person’s first step easier.",
      },
    ],
    related: ["iceland-developer-community/get-involved", "share-a-side-project"],
    action: { href: "/projects", label: "Explore projects you could help" },
  },
  {
    slug: "contribute-to-projects/first-contribution",
    kind: "spoke",
    parent: "contribute-to-projects",
    title: "Your first software-project contribution: a checklist",
    description: "Choose a small contribution, check the project’s instructions, agree on scope, and deliver work that a maintainer can review.",
    summary: "For a first contribution, pick a task you can explain in one sentence and finish with a clear handoff. Read the project’s instructions, confirm the work is wanted, make the smallest useful change, and describe how you checked it.",
    updated: "2026-09-29",
    sections: [
      {
        id: "before-you-start",
        title: "Check the project before choosing a task",
        body: "Read its description and try the part that interests you. If it links to a repository, look for the README, contribution instructions, existing issues, and any conduct guidelines. Check whether someone is already working on your proposed task.\n\nFor example, [Naglasúpan’s own repository](https://github.com/alexcouper/nglspn) is linked from this site’s footer. Its repository documentation is the starting point for work on this platform; do not assume another project uses the same stack or workflow. If a project has no public repository, you may still be able to help through a bug report or a review of its interface.",
      },
      {
        id: "pick-a-small-task",
        title: "Define one result and ask whether it would help",
        body: "Good first tasks have a visible finish: reproduce one bug, clarify one setup step, or check one screen at a narrow width. Avoid choosing a broad rewrite before you understand the project’s constraints.\n\nSend a brief proposal: “The setup guide does not explain which command starts the frontend. I can try the current steps and propose a small documentation edit. Is that useful, and is anyone already handling it?”\n\nThe maintainer may suggest a different task. Clarifying the scope before starting saves both of you review work. If there is no response, choose another documented task or project rather than assuming approval for a large change.",
      },
      {
        id: "prepare-the-handoff",
        title: "Deliver something a reviewer can check",
        body: "Follow the project’s submission process. For a code change, use its documented development and test commands. For a report, include the environment, steps to reproduce, expected result, and actual result. For documentation, try the revised instructions from the reader’s starting point.\n\nUse this handoff checklist:\n\n- State the problem and link to the agreed task, if there is one.\n- Explain the change or observation in a few sentences.\n- Describe the checks you actually performed.\n- Identify anything incomplete or uncertain.\n- Ask the reviewer a specific question if you need a decision.\n\nKeep private information out of screenshots and logs you submit publicly.",
      },
      {
        id: "after-review",
        title: "Respond to review and decide on a next step",
        body: "Treat review comments as information about the project’s needs. Ask for clarification if a requested change is unclear, and explain if it exceeds the time you can offer. Acceptance is the maintainer’s decision; submitting work does not guarantee it will be included.\n\nOnce the task is finished, note any missing instructions that would help the next newcomer. You can stop there or agree on another small task. For more context on participating in public repositories, see GitHub’s [guide to contributing to open source](https://opensource.guide/how-to-contribute/). If you want a longer collaboration, make the responsibilities explicit using a [collaboration brief](/guides/contribute-to-projects/find-collaborators).",
      },
    ],
    related: ["iceland-developer-community/find-projects", "contribute-to-projects/find-collaborators"],
    action: { href: "/projects", label: "Choose a project" },
  },
  {
    slug: "contribute-to-projects/find-collaborators",
    kind: "spoke",
    parent: "contribute-to-projects",
    title: "How to find collaborators for a side project",
    description: "Write a clear collaboration brief that explains your side project, the help you need, the time commitment, and the first task.",
    summary: "Make the request small enough to answer. Explain the project, show what exists, name the help you need, and propose a first task with a clear stopping point. Be explicit about time, payment expectations, and how decisions will be made.",
    updated: "2026-09-29",
    sections: [
      {
        id: "show-the-starting-point",
        title: "Show what exists before describing the ambition",
        body: "A collaborator needs to understand both the purpose and the starting point. Link to a project page, demo, screenshots, or a repository that they can inspect. Explain the problem in ordinary language and identify what is currently blocked.\n\n“Help build the future of local events” is difficult to act on. “The event list works, but we need help testing whether people can find events near them on mobile” gives a potential contributor something to assess. Prepare the [project page](/guides/share-a-side-project/project-page-checklist) before sending people to it.",
      },
      {
        id: "collaboration-brief",
        title: "A collaboration brief you can adapt",
        body: "Write down these details before asking someone to join:\n\n- **Purpose:** the person and problem the project serves.\n- **Current state:** what works and where to see it.\n- **Help needed:** a task and the skill it calls for.\n- **First result:** what a finished first contribution would look like.\n- **Commitment:** the time you can each offer and any timing constraints.\n- **Working arrangement:** whether the contribution is voluntary or paid, without implying either by omission.\n- **Coordination:** who reviews the work, where you will communicate, and how you will credit contributions.\n\nFor example: “I have a working event-list prototype. I’m looking for someone to review the mobile filters and send annotated screenshots. This is a voluntary one-off review; I can answer questions this weekend and will credit the contribution with your permission.”",
      },
      {
        id: "share-the-request",
        title: "Put the request where people can understand the context",
        body: "Share the brief alongside your project’s description or an update, then link to it when introducing the work in the community. The [community contact page](/about/contact) provides a route to Naglasúpan’s discussion channels. Follow the expectations of whichever space you use.\n\nInvite questions and make it easy to decline. Avoid sending a generic recruitment message to every creator in the directory. If someone has relevant work, mention the specific connection and ask whether they would like to discuss the task. A directory listing alone does not mean someone is available for collaboration.",
      },
      {
        id: "try-working-together",
        title: "Start with one task before expanding the commitment",
        body: "Agree on the deliverable and review process before work begins. After the first task, discuss what went well, what was unclear, and whether both people want to continue. Update the brief if the scope changes.\n\nKeep access and responsibility proportionate to the task. Record important decisions somewhere both contributors can find them, and agree on how to hand work back if either person needs to stop. The [first-contribution checklist](/guides/contribute-to-projects/first-contribution) can help the new collaborator prepare a clear handoff while you make time to review it.",
      },
    ],
    related: ["contribute-to-projects/first-contribution", "share-a-side-project/get-useful-feedback"],
    action: { href: "/my-projects", label: "Add context to your project" },
  },
];

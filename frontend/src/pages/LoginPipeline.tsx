// Recruiter-facing explanation of the pipeline behind Sponsr (matching engine + Sponsr), shown under the sign-in form.
// Every claim is verified against the code and production data (2026-11-26): keep it that way when editing.
const STATS = [
  { value: "240+", label: "employers tracked" },
  { value: "26k", label: "roles scanned" },
  { value: "7", label: "MCP tools" },
  { value: "278", label: "eval cases" },
];

const STEPS = [
  {
    title: "Collection",
    text: "Scheduled collectors read public applicant-tracking systems (Greenhouse, Lever, Ashby, Workday, SmartRecruiters and more) and track every change to each posting.",
    tags: ["Python", "FastAPI", "SQL Server"],
  },
  {
    title: "Sponsor licence check",
    text: "Every employer is matched against the official UK and Dutch sponsor registers with normalised and fuzzy legal-name matching. Unlicensed employers never reach the feed.",
    tags: ["Public registers", "Fuzzy matching"],
  },
  {
    title: "Rules before models",
    text: "Deterministic filters in code drop about 97% of postings before any model call, which keeps cost proportional to real candidates.",
    tags: ["Deterministic", "Cost control"],
  },
  {
    title: "Grounded Claude evaluation",
    text: "Claude on Amazon Bedrock assesses each role with structured output. A sponsorship claim only counts if code finds its verbatim quote in the posting, and scores are computed in code. The model was chosen by evaluating two Claude models on 278 real cases, balancing quality against cost.",
    tags: ["Claude on Bedrock", "Structured output", "LLM evaluation"],
  },
  {
    title: "Daily feed refresh",
    text: "The matching engine runs separately from this app. Once a day it sends the newly ranked roles here through a secured, key-protected import endpoint, so the feed you swipe is always up to date.",
    tags: ["Scheduled job", "Secure API"],
  },
  {
    title: "Swipe for a tailored CV",
    text: "Swipe right and Claude Sonnet writes a CV for that role from verified facts only. Every line must cite fact ids; code removes any line with an unsupported claim or number, then renders an ATS-friendly PDF. The prompt is ordered for caching: tools, instructions and the candidate's facts come first and are cached, the job posting goes last, so the second CV in a session reads about 77% of its prompt from cache ($0.033 instead of $0.050). Token use and cost are shown on every application.",
    tags: ["Claude Sonnet", "Tool use", "Prompt caching", "ReportLab"],
  },
  {
    title: "Use it from Claude or ChatGPT",
    text: "A remote MCP server exposes 7 tools: find sponsored jobs, job details, create a tailored CV, show a CV, open the job post, list my CVs and my profile. It works as a custom connector in claude.ai and ChatGPT, signing in through OAuth with a Sponsr login page. A CV comes back in the chat with a PDF link, and tool descriptions are written so the assistant uses Sponsr instead of writing the CV itself.",
    tags: ["MCP", "OAuth 2.1", "Claude", "ChatGPT"],
  },
  {
    title: "The app",
    text: "A React swipe deck with Framer Motion, in-app PDF preview, and a FastAPI backend with JWT cookie sessions. The Applications page refreshes itself, so CVs started from Claude or ChatGPT appear on their own.",
    tags: ["React", "Framer Motion", "pdf.js", "JWT"],
  },
];

export default function LoginPipeline() {
  return (
    <section className="login-pipeline" aria-labelledby="how-title">
      <p className="lp-eyebrow">How Sponsr works</p>
      <h3 id="how-title">An evidence-first job pipeline</h3>
      <p className="lp-intro">
        Code does the checking and Claude does the reading: nothing reaches the feed, and nothing goes into a CV,
        without evidence behind it.
      </p>
      <dl className="lp-stats">
        {STATS.map((s) => (
          <div key={s.label}>
            <dt>{s.value}</dt>
            <dd>{s.label}</dd>
          </div>
        ))}
      </dl>
      <ol className="lp-steps">
        {STEPS.map((step, i) => (
          <li key={step.title}>
            <span className="lp-num">{i + 1}</span>
            <div>
              <h4>{step.title}</h4>
              <p>{step.text}</p>
              <div className="lp-tags">{step.tags.map((t) => <span key={t}>{t}</span>)}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

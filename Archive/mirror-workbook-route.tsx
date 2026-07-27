import { useState } from "react";

export default function MirrorWorkbook() {
  const [showModules, setShowModules] = useState(false);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Hero */}
      <section className="relative px-6 py-24 md:py-32 max-w-5xl mx-auto text-center">
        <div className="mb-6 inline-block px-4 py-1 border border-zinc-700 rounded-full text-sm text-zinc-400">
          A healing tool for young people who survived trauma
        </div>
        <h1 className="text-5xl md:text-7xl font-bold mb-6 tracking-tight">
          The Mirror<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-500">Workbook</span>
        </h1>
        <p className="text-xl md:text-2xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Understanding Your Story to Change Your Life
        </p>
        <p className="text-lg text-zinc-500 max-w-xl mx-auto mb-12">
          Nine modules written by someone who was them. For the kid sitting in a cell right now wondering if this is all there is.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <a href="#get-it" className="px-8 py-4 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold rounded-lg transition-colors">
            Get the Workbook — Free for Programs
          </a>
          <button onClick={() => setShowModules(!showModules)} className="px-8 py-4 border border-zinc-700 hover:border-zinc-500 rounded-lg transition-colors">
            {showModules ? "Hide" : "See"} All 9 Modules
          </button>
        </div>
      </section>

      {/* Modules */}
      {showModules && (
        <section className="px-6 py-16 max-w-4xl mx-auto border-t border-zinc-800">
          <h2 className="text-2xl font-bold mb-8 text-center">The Nine Modules</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              { num: "1", title: "Who Am I Really?", desc: "Identity before the wound" },
              { num: "2", title: "The First Wound", desc: "Original loss and how it set the template" },
              { num: "3", title: "The Armor", desc: "Survival behaviors that stopped serving you" },
              { num: "4", title: "The Lies We Believe", desc: "Cognitive distortions and the stories that keep you stuck" },
              { num: "5", title: "The Grief You Never Finished", desc: "Complicated grief, witnessed death, cumulative loss" },
              { num: "6", title: "The Decision", desc: "Choosing to live before it's too late" },
              { num: "7", title: "Building the New Self", desc: "Identity reconstruction" },
              { num: "8", title: "The Work", desc: "Daily practices and the 90-day rule" },
              { num: "9", title: "The Legacy", desc: "Reaching back so the next person doesn't fall" },
            ].map((m) => (
              <div key={m.num} className="p-5 bg-zinc-900 rounded-xl border border-zinc-800">
                <div className="text-amber-500 font-bold text-sm mb-2">Module {m.num}</div>
                <h3 className="font-semibold text-lg mb-1">{m.title}</h3>
                <p className="text-zinc-500 text-sm">{m.desc}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* What It Is */}
      <section className="px-6 py-20 max-w-4xl mx-auto border-t border-zinc-800">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold mb-6">Not a textbook. Not a lecture.<br />A mirror.</h2>
            <p className="text-zinc-400 text-lg leading-relaxed mb-6">
              Most programs teach kids what they did wrong. The Mirror Workbook asks what happened to them — and helps them see that the anger they're carrying might be grief they never finished.
            </p>
            <p className="text-zinc-400 text-lg leading-relaxed">
              It walks young people through understanding their armor, naming the lies they believe, finishing their grief, and choosing — on purpose — to build something different.
            </p>
          </div>
          <div className="bg-zinc-900 rounded-2xl p-8 border border-zinc-800">
            <h3 className="font-semibold text-lg mb-4 text-amber-400">Grounded in research:</h3>
            <ul className="space-y-3 text-zinc-400">
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>Attachment Theory</span></li>
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>ACEs Framework (Adverse Childhood Experiences)</span></li>
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>Complex PTSD (Judith Herman)</span></li>
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>Somatic Trauma Therapy (Peter Levine)</span></li>
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>Cognitive Behavioral Therapy</span></li>
              <li className="flex items-start gap-3"><span className="text-amber-500 mt-1">•</span><span>Post-Traumatic Growth Research</span></li>
            </ul>
          </div>
        </div>
      </section>

      {/* Who It's For */}
      <section className="px-6 py-20 bg-zinc-900 border-y border-zinc-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Who It's For</h2>
          <p className="text-zinc-400 text-lg mb-10">Young people ages 14–24 who have survived trauma, loss, and systems designed to break them.</p>
          <div className="flex flex-wrap justify-center gap-3">
            {["Juvenile detention", "Group homes", "Foster care", "Reentry programs", "Alternative schools", "Residential treatment", "Homelessness programs", "Youth mentorship"].map(tag => (
              <span key={tag} className="px-4 py-2 bg-zinc-800 rounded-full text-sm text-zinc-300">{tag}</span>
            ))}
          </div>
        </div>
      </section>

      {/* Author */}
      <section className="px-6 py-20 max-w-4xl mx-auto">
        <div className="bg-gradient-to-br from-zinc-900 to-zinc-800 rounded-2xl p-8 md:p-12 border border-zinc-700">
          <h2 className="text-3xl font-bold mb-6">About the Author</h2>
          <div className="flex flex-col md:flex-row gap-8">
            <div className="flex-1">
              <p className="text-zinc-300 text-lg leading-relaxed mb-4">
                <strong className="text-white">Tyson DePina</strong> is a 49-year-old Cape Verdean man from New Bedford, Massachusetts. He spent <strong className="text-amber-400">24 of his first 38 years</strong> in and out of prison — including 8 years in federal prison.
              </p>
              <p className="text-zinc-400 leading-relaxed mb-4">
                He wrote <em>The Mirror Workbook</em> for the kid he was: a young person who survived trauma, was told he was a problem, and never got the help he needed to understand why.
              </p>
              <p className="text-zinc-500 italic">
                "Reaching back so the next person doesn't fall."
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="get-it" className="px-6 py-24 bg-zinc-900 border-t border-zinc-800">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Free for Organizations Serving At-Risk Youth</h2>
          <p className="text-zinc-400 text-lg mb-8">
            No application. No cost. Just a tool that works — from someone who knows.
          </p>
          <div className="bg-zinc-800 rounded-xl p-6 border border-zinc-700">
            <p className="text-zinc-300 mb-2">Contact Tyson DePina:</p>
            <p className="text-xl font-semibold mb-1">📞 508-639-4473</p>
            <p className="text-amber-400">✉️ tysonjdepina76@gmail.com</p>
          </div>
        </div>
      </section>

      <footer className="px-6 py-8 border-t border-zinc-800 text-center text-zinc-600 text-sm">
        <p>The Mirror Workbook · Tyson DePina · New Bedford, MA</p>
      </footer>
    </div>
  );
}

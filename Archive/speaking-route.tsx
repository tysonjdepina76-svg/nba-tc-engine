import { useState } from "react";
import { Mic, Mail, MapPin, Calendar, Users, BookOpen } from "lucide-react";

export default function Speaking() {
  const [form, setForm] = useState({ name: "", email: "", org: "", message: "" });
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const subject = `Speaking Inquiry from ${form.name}${form.org ? ` (${form.org})` : ""}`;
    const body = `Name: ${form.name}\nEmail: ${form.email}\nOrganization: ${form.org || "N/A"}\n\nMessage:\n${form.message}`;
    window.location.href = `mailto:tysonjdepina76@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    setSent(true);
  };

  const topics = [
    {
      icon: <BookOpen className="w-6 h-6" />,
      title: "AI & Second Chances: Reentry in the Age of Technology",
      desc: "I didn't just come home — I built. Eight months out of federal prison, I taught myself to work with AI and built a live sports analytics pipeline with dashboards, APIs, and backtests. This talk is for tech companies, universities, and anyone who needs proof that second chances produce first-rate results.",
      featured: true,
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: "From the System to the Solution",
      desc: "24 years in and out of prison. Federal time. What the system does to a person — and what it almost didn't let me become. The turning point that made me say 'I'm not dying in prison.'",
    },
    {
      icon: <Mic className="w-6 h-6" />,
      title: "The Mirror: Reaching Youth Before They Fall",
      desc: "Built for system-involved youth, juvenile justice programs, and schools. The Mirror Workbook approach — giving kids the language for pain they don't have words for yet.",
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      title: "Reentry & Second Chances",
      desc: "Practical wisdom for organizations working with returning citizens. Employment barriers, housing challenges, and the mental health piece nobody talks about.",
    },
    {
      icon: <Mic className="w-6 h-6" />,
      title: "Cape Verdean Resilience",
      desc: "Growing up Cape Verdean in New Bedford. Cultural identity, community violence, and breaking generational cycles. For community organizations, cultural events, and youth groups.",
    },
  ];

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      <div className="relative overflow-hidden bg-zinc-900 border-b border-zinc-800">
        <div className="absolute inset-0 bg-gradient-to-br from-amber-900/20 to-zinc-950" />
        <div className="relative max-w-4xl mx-auto px-6 py-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1 bg-amber-600 text-white text-sm font-medium rounded-full mb-6">
            <Mic className="w-4 h-4" /> Available for Speaking
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-4">Book Tyson to Speak</h1>
          <p className="text-xl text-zinc-300 font-light max-w-2xl mx-auto">
            Keynotes, panels, workshops, and community conversations. I don't just talk about the work — I lived it.
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-16">
        <section className="mb-20">
          <h2 className="text-3xl font-bold text-amber-400 mb-8 text-center">Speaking Topics</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {topics.map((topic, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 hover:border-amber-700 transition-colors">
                <div className="text-amber-500 mb-4">{topic.icon}</div>
                <h3 className="text-xl font-bold mb-3">{topic.title}</h3>
                <p className="text-zinc-400 leading-relaxed">{topic.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-20">
          <h2 className="text-3xl font-bold text-amber-400 mb-8 text-center">Who I Speak To</h2>
          <div className="grid md:grid-cols-5 gap-4 text-center">
            {[
              { label: "Tech & Universities", desc: "ERGs, CS depts, reentry-in-tech" },
              { label: "Youth Programs", desc: "Juvenile justice, schools, after-school" },
              { label: "Reentry Orgs", desc: "Nonprofits, halfway houses, workforce dev" },
              { label: "Universities", desc: "Criminal justice, social work, psychology" },
              { label: "Community Events", desc: "Churches, cultural orgs, panels" },
            ].map((a, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                <div className="text-amber-500 font-bold text-lg mb-2">{a.label}</div>
                <p className="text-zinc-500 text-sm">{a.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold text-amber-400 mb-8 text-center">Book a Conversation</h2>
          {sent ? (
            <div className="bg-zinc-900 border border-amber-700 rounded-xl p-10 text-center">
              <div className="text-4xl mb-4">✅</div>
              <h3 className="text-xl font-bold mb-2">Message Sent</h3>
              <p className="text-zinc-400">
                Your email client should open. If it didn't, email me directly at{" "}
                <span className="text-amber-400">tysonjdepina76@gmail.com</span>.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 space-y-6">
              <div><label className="block text-sm text-zinc-400 mb-2">Your Name</label><input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-colors" placeholder="Your full name" /></div>
              <div><label className="block text-sm text-zinc-400 mb-2">Email</label><input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-colors" placeholder="you@example.com" /></div>
              <div><label className="block text-sm text-zinc-400 mb-2">Organization</label><input type="text" value={form.org} onChange={e => setForm({ ...form, org: e.target.value })} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-colors" placeholder="School, nonprofit, company..." /></div>
              <div><label className="block text-sm text-zinc-400 mb-2">What are you looking for?</label><textarea required value={form.message} onChange={e => setForm({ ...form, message: e.target.value })} rows={4} className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-colors resize-none" placeholder="Event type, date, audience..." /></div>
              <button type="submit" className="w-full bg-amber-600 hover:bg-amber-500 text-black font-bold py-4 rounded-lg transition-colors flex items-center justify-center gap-2"><Mail className="w-5 h-5" />Send Inquiry</button>
              <p className="text-zinc-600 text-xs text-center">Opens your email client. Prefer direct? Email tysonjdepina76@gmail.com</p>
            </form>
          )}
        </section>

        <div className="max-w-2xl mx-auto mt-12 grid md:grid-cols-2 gap-6">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 flex items-start gap-4"><MapPin className="w-5 h-5 text-amber-500 mt-1 flex-shrink-0" /><div><h4 className="font-bold mb-1">Location</h4><p className="text-zinc-400 text-sm">Based in New Bedford, Massachusetts. Willing to travel nationally.</p></div></div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 flex items-start gap-4"><Calendar className="w-5 h-5 text-amber-500 mt-1 flex-shrink-0" /><div><h4 className="font-bold mb-1">Availability</h4><p className="text-zinc-400 text-sm">Keynotes, panels, workshops. Virtual and in-person. Flexible scheduling.</p></div></div>
        </div>

        <div className="text-center mt-16"><a href="/" className="text-zinc-500 hover:text-amber-400 text-sm transition-colors">← Back to Home</a></div>
      </div>

      <div className="border-t border-zinc-800 mt-16"><div className="max-w-4xl mx-auto px-6 py-8 text-center"><p className="text-zinc-500 text-sm">© 2026 Tyson DePina · New Bedford, MA</p></div></div>
    </main>
  );
}
